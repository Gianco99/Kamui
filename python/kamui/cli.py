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
import subprocess
import sys

## Kamui modules
from .grid import das, fetch
from .foundations import paths
from .helpers.banner import printBanner
from .configReaders.catalog import loadCatalog, select
from .configReaders.content import listPresets, resolveContent, summarize, validateTriggers
from .submit import condor as condorBackend, crab as crabBackend
from .configReaders.sites import loadSites
from .submit.common import taskDir

# Sample Selection Helper Functions
## These come first because other functions later on depend on them to work.

def _addSelection(p):
    """
    Gives a sample-related command defined in main() the five sample selection flags.
    Sample convention documented in Kamui/config/samples/README.txt
    """
    p.add_argument("--name", action="append", help="Exact sample name")
    p.add_argument("--family", help="Family file name, e.g. exoticHiggs4d2024")
    p.add_argument("--era", help="Data-taking period, e.g. Summer24, Summer23, 2018, ...")
    p.add_argument("--tag", help="Tag from the sample config, e.g. signal / stealthSusy")
    p.add_argument("--match", help="Wildcard on the sample name, e.g. 'ggH*ctau10mm*'")

def _pick(args, required=True):
    """
    Turns whatever the user passed into an actual list of samples.
    """
    cat = loadCatalog()
    sel = select(cat, names=args.name, family=args.family, era=args.era, tag=args.tag, pattern=args.match)
    if required and not sel:
        sys.exit("No samples matched the selection (try `kamui list`)")
    return sel


# Commands!

def _cmdList(args):
    """List catalog entries. With no selection flags, lists the whole catalog."""
    sel = _pick(args, required=False)
    if args.datasets:
        for s in sel:
            print(s["dataset"])
        return
    fams = {}
    for s in sel:
        fams.setdefault(s.get("family", "?"), []).append(s)
    ## Widths from the data, so a long preset name does not push the tags out of line
    wName = max([len(s["name"]) for s in sel] + [4])
    wEra = max([len(s.get("era", "-")) for s in sel] + [3])
    wContent = max([len(s["content"]) for s in sel] + [7])
    for fam in sorted(fams):
        print(f"\n{fam}  ({len(fams[fam])} samples)")
        for s in sorted(fams[fam], key=lambda x: x["name"]):
            print(f"  {s['name']:<{wName}}  {s.get('era','-'):<{wEra}}  {s['content']:<{wContent}}  {','.join(s['tags'])}")
    print(f"\n{len(sel)} sample(s) total")


def _cmdContent(args):
    """Show what a content preset writes out: collections, variables, skim and MiniAOD groups. With no preset name, lists the presets available."""
    if not args.preset:
        for group, names in listPresets().items():
            print(f"{group or 'content'}: " + ", ".join(names))
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


def _cmdQuery(args):
    """Ask DAS how many files, events and GB each selected sample holds. Needs cmsenv and a grid proxy."""
    sel = _pick(args)
    totF = totE = totS = 0
    w = max([len(s["name"]) for s in sel] + [len("TOTAL")])
    print(f"{'sample':<{w}} {'files':>7} {'events':>12} {'size/GB':>9}")
    for s in sel:
        info = das.datasetSummary(s["dataset"], s["dasInstance"], refresh=args.refresh)
        print(f"{s['name']:<{w}} {info['nfiles']:>7} {info['nevents']:>12,} {info['sizeGB']:>9.1f}")
        totF += info["nfiles"]; totE += info["nevents"]; totS += info["sizeGB"]
    print(f"{'TOTAL':<{w}} {totF:>7} {totE:>12,} {totS:>9.1f}")


def _cmdFind(args):
    """Search DAS for datasets matching a wildcard pattern. Needs cmsenv and a grid proxy."""
    hits = das.findDatasets(args.pattern, args.instance, refresh=args.refresh)
    for h in hits:
        print(h)
    print(f"\n{len(hits)} dataset(s)")


def _cmdStage(args):
    """Copy raw MiniAOD files to our EOS area. For inspecting files and prototyping content presets."""
    sites = loadSites()
    sel = _pick(args)
    for s in sel:
        print(f"\n=== {s['name']}\n  {s['dataset']}")
        fetch.stage(s, sites, quick=not args.full, maxFiles=args.maxFiles, dryRun=args.dryRun, refresh=args.refresh)


def _cmdSubmit(args):
    """Build a job area for the selected samples and submit it. Use --dry-run first for testing."""
    sel = _pick(args)
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
        cfgs, task = crabBackend.prepare(sel, args.task, unitsPerJob=args.filesPerJob, maxMemoryMB=args.memoryMB, output=args.output, assumeYes=args.yes)
        print(f"  wrote {len(cfgs)} crab config(s) under {taskDir(task, create=False)}")
        crabBackend.submit(cfgs, dryRun=args.dryRun, taskName=task)
    else:
        fileLists = {}
        for s in sel:
            lfns = das.listFiles(s["dataset"], s["dasInstance"], refresh=args.refresh)
            if args.quick and s.get("nFilesFor10k"):
                lfns = lfns[: s["nFilesFor10k"]]
            fileLists[s["name"]] = lfns
            print(f"  {s['name']:<48} {len(lfns):>5} file(s)")
        d, nJobs, task = condorBackend.prepare(sel, args.task, fileLists, filesPerJob=args.filesPerJob, memoryMB=args.memoryMB, output=args.output, assumeYes=args.yes)
        print(f"  wrote {nJobs} job(s) under {d}")
        condorBackend.submit(task, dryRun=args.dryRun)


def _cmdStatus(args):
    """Show what a task submitted and its current batch status."""
    d = taskDir(args.task, create=False)
    rec = os.path.join(d, "task.json")
    if not os.path.exists(rec):
        sys.exit(f"no task '{args.task}' under {paths.JOBS_DIR}")
    with open(rec) as f:
        info = json.load(f)

    # Print the few lines that matter; the record embeds every resolved preset and runs to tens of kB.
    prov = info.get("provenance", {})
    print(f"task     {info.get('task')}  ({info.get('backend')}, output={info.get('output')})")
    print(f"samples  {len(info.get('samples', []))}, content {', '.join(info.get('content') or sorted({c for c in [d.get('content') for d in info.get('sampleDetails', [])] if c}))}")
    if info.get("nJobs") is not None:
        print(f"jobs     {info['nJobs']}")
    if prov:
        dirty = " (dirty tree)" if prov.get("dirty") else ""
        print(f"from     {str(prov.get('commit'))[:8]} on {prov.get('branch')}{dirty}, by {prov.get('submittedBy')} at {prov.get('submittedAt')}")
    print(f"output   {info.get('outLFNDirBase') or info.get('outDirBase')}")
    print(f"record   {rec}")

    if info.get("backend") == "crab":
        crabBackend.status(args.task)
    else:
        cluster = info.get("condorCluster")
        cmd = ["condor_q", "-nobatch"] + ([str(cluster)] if cluster else [])
        if not cluster:
            print("\n(no cluster id recorded; showing every job you have queued)")
        subprocess.run(cmd)


def _cmdCheck(args):
    """Offline validation of every config file."""
    problems = []
    cat = loadCatalog()
    print(f"catalog : {len(cat)} samples in " f"{len({s.get('family') for s in cat})} families")

    presets = [n for names in listPresets().values() for n in names]
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


def _cmdCache(args):
    """Inspect, prune or clear the on-disk cache of DAS responses."""
    if args.clear:
        das.clearCache()
        print("DAS cache cleared")
        return
    if args.prune:
        print(f"pruned {das.pruneCache()} expired entry(s)")
    st = das.cacheStats()
    print(f"{st['n']} cached DAS response(s), {st['bytes'] / 1e6:.1f} MB in {st['dir']}")
    if st["n"]:
        print(f"  age      {st['newestDays']:.1f} to {st['oldestDays']:.1f} days")
        print(f"  expired  {st['nStale']} (older than {das.CACHE_MAX_AGE_DAYS} days, ignored on read)")


# Parser!
def main(argv=None):
    p = argparse.ArgumentParser(prog="kamui", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-banner", dest="noBanner", action="store_true", help="Skip the startup banner")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("list", help="Show all catalog entries", description=_cmdList.__doc__)
    _addSelection(q)
    q.add_argument("--datasets", action="store_true", help="Print DAS paths only")
    q.set_defaults(func=_cmdList)

    q = sub.add_parser("content", help="Show or export a content preset", description=_cmdContent.__doc__)
    q.add_argument("preset", nargs="?", help="Preset name; omit to list them")
    q.add_argument("--data", action="store_true", help="Resolve as data (drops mcOnly collections)")
    q.add_argument("--write", help="Write the resolved JSON here")
    q.set_defaults(func=_cmdContent)

    q = sub.add_parser("query", help="DAS file/event/size counts (needs a proxy)", description=_cmdQuery.__doc__)
    _addSelection(q)
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdQuery)

    q = sub.add_parser("find", help="Free-form DAS dataset search", description=_cmdFind.__doc__)
    q.add_argument("pattern", help="DAS wildcard, e.g. '/*HAHM*/*/MINIAODSIM'")
    q.add_argument("--instance", default="prod/global", help="prod/global for official datasets, prod/phys03 for USER ones")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdFind)

    q = sub.add_parser("stage", help="Copy raw MiniAOD to EOS (small test samples)", description=_cmdStage.__doc__)
    _addSelection(q)
    q.add_argument("--full", action="store_true", help="Copy the whole dataset, not just nFilesFor10k")
    q.add_argument("--maxFiles", type=int, help="Hard cap on files copied")
    q.add_argument("--dry-run", dest="dryRun", action="store_true", help="Print what would be copied, copy nothing")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdStage)

    q = sub.add_parser("submit", help="Produce ntuples", description=_cmdSubmit.__doc__)
    _addSelection(q)
    q.add_argument("--task", required=True, help="Task name; also the EOS output subdirectory")
    q.add_argument("--backend", choices=["crab", "condor"], default="crab", help="Where the jobs run (default: crab)")
    q.add_argument("--content", help="Override the per-sample content preset")
    q.add_argument("--output", choices=["ntuple", "miniaod", "both"], default="ntuple", help="What each job writes (default: ntuple)")
    q.add_argument("--filesPerJob", type=int, help="Input files per job, overriding any per-sample unitsPerJob (default: 5)")
    q.add_argument("--memoryMB", type=int, default=2500, help="Memory request per job in MB (default: 2500)")
    q.add_argument("--quick", action="store_true", help="Condor only: cap at nFilesFor10k")
    q.add_argument("--dry-run", dest="dryRun", action="store_true", help="Write the job area, submit nothing")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.add_argument("--yes", action="store_true", help="Overwrite an existing job area without asking")
    q.set_defaults(func=_cmdSubmit)

    q = sub.add_parser("status", help="Status of a submitted task", description=_cmdStatus.__doc__)
    q.add_argument("--task", required=True, help="Task name under production/jobs/")
    q.set_defaults(func=_cmdStatus)

    q = sub.add_parser("check", help="Validate every config offline", description=_cmdCheck.__doc__)
    q.set_defaults(func=_cmdCheck)

    q = sub.add_parser("cache", help="Inspect or clear the DAS cache", description=_cmdCache.__doc__)
    q.add_argument("--clear", action="store_true", help="Delete every cached response")
    q.add_argument("--prune", action="store_true", help="Delete only the expired entries, keeping the rest")
    q.set_defaults(func=_cmdCache)

    printBanner(enabled="--no-banner" not in (argv if argv is not None else sys.argv))
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, FileNotFoundError, ValueError, das.DasError) as e:
        # Config and DAS problems are user errors - say what is wrong and stop.
        # Anything else still raises.
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    sys.exit(main())
