#!/usr/bin/env python3
"""
Kamui - the CLI for the analysis framework. 
See python/kamui/README.txt for what each command does and the flags they take.
"""

# Import Block

## Standard Python imports
import argparse
import json
import os
import sys

## Kamui modules
from . import das
from . import fetch
from .foundations import paths
from .helpers.banner import printBanner
from .configReaders.catalog import loadCatalog, select
from .foundations.config import loadWithIncludes
from .configReaders.content import listPresets, resolveContent, summarize, validateTriggers
from .submit import condor as condorBackend, crab as crabBackend
from .configReaders.sites import loadSites
from .submit.common import taskDir

# Sample Selection Helper Functions
## These come first because other functions later on depend on them to work.

def addSelection(p):
    """
    Gives a sample-related command defined in main() the five sample selection flags.
    Sample convention documented in Kamui/SamplesFromDAS/config/samples/README.txt
    """
    p.add_argument("--name", action="append", help="Exact sample name")
    p.add_argument("--family", help="Family file name, e.g. exoticHiggs4d2024")
    p.add_argument("--era", help="Data-taking period, e.g. Summer24, Summer23, 2018, ...")
    p.add_argument("--tag", help="Tag from the sample config, e.g. signal / stealthSusy")
    p.add_argument("--match", help="Wildcard on the sample name, e.g. 'ggH*ctau10mm*'")

def pick(args, required=True):
    """
    Turns whatever the user passed into an actual list of samples.
    """
    cat = loadCatalog()
    sel = select(cat, names=args.name, family=args.family, era=args.era, tag=args.tag, pattern=args.match)
    if required and not sel:
        sys.exit("No samples matched the selection (try `kamui list`)")
    return sel


# Commands!

def cmdList(args):
    """List catalog entries. With no selection flags, lists the whole catalog."""
    sel = pick(args, required=False)
    if args.datasets:
        for s in sel:
            print(s["dataset"])
        return
    fams = {}
    for s in sel:
        fams.setdefault(s.get("family", "?"), []).append(s)
    for fam in sorted(fams):
        print(f"\n{fam}  ({len(fams[fam])} samples)")
        for s in sorted(fams[fam], key=lambda x: x["name"]):
            print(f"  {s['name']:<48} {s.get('era','-'):<10} {s['content']:<10} {','.join(s['tags'])}")
    print(f"\n{len(sel)} sample(s) total")


def cmdContent(args):
    """Show what a content preset writes out: collections, variables, skim and MiniAOD groups. With no preset name, lists the presets available."""
    if not args.preset:
        print("presets: " + ", ".join(listPresets()))
        return
    resolved = resolveContent(args.preset, isMC=not args.data)
    print(f"{args.preset}  (isMC={not args.data})")
    print(summarize(resolved))
    nvar = sum(len(c.get("variables", c.get("extVariables", {}))) for c in resolved["collections"].values())
    print(f"\n  {len(resolved['collections'])} collections, {nvar} variables")
    if resolved["skim"]:
        print(f"  skim: {resolved['skim']}")
    if args.write:
        with open(args.write, "w") as f:
            json.dump(resolved, f, indent=2)
        print(f"  wrote {args.write}")


def cmdQuery(args):
    """Ask DAS how many files, events and GB each selected sample holds. Needs cmsenv and a grid proxy."""
    sel = pick(args)
    totF = totE = totS = 0
    print(f"{'sample':<48} {'files':>7} {'events':>12} {'size/GB':>9}")
    for s in sel:
        try:
            info = das.datasetSummary(s["dataset"], s["dasInstance"], refresh=args.refresh)
        except das.DasError as e:
            sys.exit(str(e))
        print(f"{s['name']:<48} {info['nfiles']:>7} {info['nevents']:>12,} {info['sizeGB']:>9.1f}")
        totF += info["nfiles"]; totE += info["nevents"]; totS += info["sizeGB"]
    print(f"{'TOTAL':<48} {totF:>7} {totE:>12,} {totS:>9.1f}")


def cmdFind(args):
    """Search DAS for datasets matching a wildcard pattern. Needs cmsenv and a grid proxy."""
    hits = das.findDatasets(args.pattern, args.instance, refresh=args.refresh)
    for h in hits:
        print(h)
    print(f"\n{len(hits)} dataset(s)")


def cmdStage(args):
    """Copy raw MiniAOD files to our EOS area. For inspecting files and prototyping content presets - use submit for production, not this."""
    sites = loadSites()
    sel = pick(args)
    for s in sel:
        print(f"\n=== {s['name']}\n  {s['dataset']}")
        fetch.stage(s, sites, quick=not args.full, maxFiles=args.maxFiles, dryRun=args.dryRun, refresh=args.refresh)


def cmdSubmit(args):
    """Build a job area for the selected samples and submit it. Use --dry-run first: it writes the complete job area and submits nothing."""
    sel = pick(args)
    if args.content:                       # override the per-sample preset
        for s in sel:
            s["content"] = args.content
    print(f"task '{args.task}' : {len(sel)} sample(s), backend={args.backend}")

    if args.output != "ntuple":
        missing = [s["name"] for s in sel if not resolveContent(s["content"], isMC=bool(s["isMC"])).get("miniaod")]
        if missing:
            sys.exit(f"error: output={args.output} but these samples' content presets define no " f"miniaod block: {missing[:5]}")
        if args.backend == "crab" and args.output == "both":
            print(" NOTE: two EDM output modules in one CRAB task is not yet verified here. " "If CRAB refuses it, run two tasks with --output ntuple and --output miniaod.")

    if args.backend == "crab":
        cfgs = crabBackend.prepare(sel, args.task, unitsPerJob=args.filesPerJob, maxMemoryMB=args.memoryMB, output=args.output)
        print(f"  wrote {len(cfgs)} crab config(s) under {taskDir(args.task, create=False)}")
        crabBackend.submit(cfgs, dryRun=args.dryRun)
    else:
        fileLists = {}
        for s in sel:
            lfns = das.listFiles(s["dataset"], s["dasInstance"], refresh=args.refresh)
            if args.quick and s.get("nFilesFor10k"):
                lfns = lfns[: s["nFilesFor10k"]]
            fileLists[s["name"]] = lfns
            print(f"  {s['name']:<48} {len(lfns):>5} file(s)")
        d, nJobs = condorBackend.prepare(sel, args.task, fileLists, filesPerJob=args.filesPerJob, memoryMB=args.memoryMB, output=args.output)
        print(f"  wrote {nJobs} job(s) under {d}")
        condorBackend.submit(args.task, dryRun=args.dryRun)


def cmdStatus(args):
    """Show what a task submitted and its current batch status."""
    d = taskDir(args.task, create=False)
    rec = os.path.join(d, "task.json")
    if not os.path.exists(rec):
        sys.exit(f"no task '{args.task}' under {paths.JOBS_DIR}")
    with open(rec) as f:
        info = json.load(f)
    print(json.dumps(info, indent=2))
    if info.get("backend") == "crab":
        crabBackend.status(args.task)
    else:
        os.system("condor_q -nobatch")


def cmdCheck(args):
    """Offline validation of every config file. No DAS, no proxy, no CMSSW."""
    problems = []
    cat = loadCatalog()
    print(f"catalog : {len(cat)} samples in " f"{len({s.get('family') for s in cat})} families")

    presets = listPresets()
    resolved = {}
    for p in presets:
        try:
            resolved[p] = resolveContent(p, isMC=True)
            resolveContent(p, isMC=False)
        except Exception as e:                                        # noqa: BLE001
            problems.append(f"content preset '{p}': {e}")
    print(f"content presets: {len(resolved)}/{len(presets)} resolve for both MC and data")

    for s in cat:
        if s["content"] not in presets:
            problems.append(f"sample '{s['name']}' wants unknown content preset '{s['content']}'")
        if not s["dataset"].startswith("/") or s["dataset"].count("/") != 3:
            problems.append(f"sample '{s['name']}' has a malformed dataset path")
    dupes = len(cat) - len({s["name"] for s in cat})
    if dupes:
        problems.append(f"{dupes} duplicate sample name(s)")

    ## foundations/ is a layer, not just a folder: nothing in it may import from above
    foundDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foundations")
    for f in sorted(x for x in os.listdir(foundDir) if x.endswith(".py")):
        for line in open(os.path.join(foundDir, f)):
            if line.startswith("from ..") or (line.startswith("from .") and not line.startswith("from ." + "foundations")):
                problems.append(f"foundations/{f} imports from above the foundation layer: {line.strip()}")

    problems += validateTriggers()

    ## configReaders/ owns the config files: nothing outside it may open one directly
    pkgDir = os.path.dirname(os.path.abspath(__file__))
    for root, _, files in os.walk(pkgDir):
        if "configReaders" in root or "__pycache__" in root:
            continue
        for f in sorted(x for x in files if x.endswith(".py")):
            for line in open(os.path.join(root, f)):
                if any("paths." + d in line for d in ("CONFIG_DIR", "SAMPLES_DIR", "CONTENT_DIR", "TRIGGERS_DIR", "SITES_FILE")):
                    problems.append(f"{os.path.relpath(os.path.join(root, f), pkgDir)} reads a config directory directly; that belongs in configReaders/")

    sites = loadSites()
    for k in ("eosRedirector", "sourceRedirector", "stageoutBase", "crabStorageSite"):
        if k not in sites:
            problems.append(f"sites.json is missing '{k}'")

    for f in ("kamuiNtuple_cfg.py", "kamuiTables.py", "inspectMiniAOD.py"):
        if not os.path.exists(os.path.join(paths.CMSSW_DIR, f)):
            problems.append(f"missing cmssw/{f}")

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  " + p)
        return 1
    print("all configs OK")
    return 0


def cmdCache(args):
    """Inspect or clear the on-disk cache of DAS responses."""
    if args.clear:
        das.clearCache()
        print("DAS cache cleared")
    else:
        n = len(os.listdir(paths.CACHE_DIR)) if os.path.isdir(paths.CACHE_DIR) else 0
        print(f"{n} cached DAS response(s) in {paths.CACHE_DIR}")


# Parser!
def main(argv=None):
    p = argparse.ArgumentParser(prog="kamui", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-banner", dest="noBanner", action="store_true", help="skip the startup banner")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("list", help="Show all catalog entries", description=cmdList.__doc__)
    addSelection(q)
    q.add_argument("--datasets", action="store_true", help="Print DAS paths only")
    q.set_defaults(func=cmdList)

    q = sub.add_parser("content", help="Show or export a content preset", description=cmdContent.__doc__)
    q.add_argument("preset", nargs="?", help="Preset name; omit to list them")
    q.add_argument("--data", action="store_true", help="Resolve as data (drops mcOnly collections)")
    q.add_argument("--write", help="Write the resolved JSON here")
    q.set_defaults(func=cmdContent)

    q = sub.add_parser("query", help="DAS file/event/size counts (needs a proxy)", description=cmdQuery.__doc__)
    addSelection(q)
    q.add_argument("--refresh", action="store_true", help="bypass the DAS cache")
    q.set_defaults(func=cmdQuery)

    q = sub.add_parser("find", help="free-form DAS dataset search", description=cmdFind.__doc__)
    q.add_argument("pattern", help="DAS wildcard, e.g. '/*HAHM*/*/MINIAODSIM'")
    q.add_argument("--instance", default="prod/global", help="prod/global for official datasets, prod/phys03 for USER ones")
    q.add_argument("--refresh", action="store_true", help="bypass the DAS cache")
    q.set_defaults(func=cmdFind)

    q = sub.add_parser("stage", help="copy raw MiniAOD to EOS (small test samples)", description=cmdStage.__doc__)
    addSelection(q)
    q.add_argument("--full", action="store_true", help="copy the whole dataset, not just nFilesFor10k")
    q.add_argument("--maxFiles", type=int, help="hard cap on files copied")
    q.add_argument("--dry-run", dest="dryRun", action="store_true", help="print what would be copied, copy nothing")
    q.add_argument("--refresh", action="store_true", help="bypass the DAS cache")
    q.set_defaults(func=cmdStage)

    q = sub.add_parser("submit", help="produce ntuples", description=cmdSubmit.__doc__)
    addSelection(q)
    q.add_argument("--task", required=True, help="task name; also the EOS output subdirectory")
    q.add_argument("--backend", choices=["crab", "condor"], default="crab", help="where the jobs run (default: crab)")
    q.add_argument("--content", help="override the per-sample content preset")
    q.add_argument("--output", choices=["ntuple", "miniaod", "both"], default="ntuple", help="what each job writes (default: ntuple)")
    q.add_argument("--filesPerJob", type=int, default=5, help="input files per job (default: 5)")
    q.add_argument("--memoryMB", type=int, default=2500, help="memory request per job in MB (default: 2500)")
    q.add_argument("--quick", action="store_true", help="condor only: cap at nFilesFor10k")
    q.add_argument("--dry-run", dest="dryRun", action="store_true", help="write the job area, submit nothing")
    q.add_argument("--refresh", action="store_true", help="bypass the DAS cache")
    q.set_defaults(func=cmdSubmit)

    q = sub.add_parser("status", help="status of a submitted task", description=cmdStatus.__doc__)
    q.add_argument("--task", required=True, help="task name under SamplesFromDAS/jobs/")
    q.set_defaults(func=cmdStatus)

    q = sub.add_parser("check", help="validate every config offline (no DAS, no CMSSW)", description=cmdCheck.__doc__)
    q.set_defaults(func=cmdCheck)

    q = sub.add_parser("cache", help="inspect or clear the DAS cache", description=cmdCache.__doc__)
    q.add_argument("--clear", action="store_true", help="delete the cache instead of describing it")
    q.set_defaults(func=cmdCache)

    printBanner(enabled="--no-banner" not in (argv if argv is not None else sys.argv))
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, FileNotFoundError, ValueError, das.DasError) as e:
        # Config and DAS problems are user errors, not crashes - say what is wrong
        # and stop. Anything else still raises, so real bugs stay visible.
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    sys.exit(main())
