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
from .configReaders.content import eraGroup, listPresets, resolveContent, summarize, validateEraCopies, validateTriggers
from .submit import condor as condorBackend, crab as crabBackend
from .select import batch as selectBatch, io as selectBackend, normalization
from .select.engine import applySelection
from .configReaders.selections import resolveSelection
from .configReaders.sites import loadSites
from .submit.common import runTool, taskDir

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
    resolved = resolveContent(args.preset, isMC=not args.data, era=args.era or "Summer24")
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
    if args.maxFiles is not None and args.maxFiles < 1:
        sys.exit(f"--maxFiles must be at least 1, got {args.maxFiles}")
    sel = _pick(args)
    problems = []
    for s in sel:
        print(f"\n=== {s['name']}\n  {s['dataset']}")
        try:
            fetch.stage(s, sites, maxFiles=args.maxFiles, dryRun=args.dryRun, refresh=args.refresh)
        except ValueError as e:
            print(f"  skipped: {e}")
            problems.append(s["name"])
    if problems:
        print(f"\n{len(problems)} sample(s) skipped: {', '.join(problems)}")
        return 1 if len(problems) == len(sel) else 0


def _cmdSubmit(args):
    """Build a job area for the selected samples and submit it. Use --dry-run first for testing."""
    sel = _pick(args)
    if args.filesPerJob is not None and args.filesPerJob < 1:
        sys.exit(f"--filesPerJob must be at least 1, got {args.filesPerJob}")
    if args.maxFiles is not None and args.maxFiles < 1:
        sys.exit(f"--maxFiles must be at least 1, got {args.maxFiles}")
    if args.content:                       # override the per-sample preset
        for s in sel:
            s["content"] = args.content
    print(f"task '{args.task}' : {len(sel)} sample(s), backend={args.backend}")

    if args.output != "ntuple":
        missing = [s["name"] for s in sel if not resolveContent(s["content"], isMC=bool(s["isMC"]), era=s["era"]).get("miniaod")]
        if missing:
            sys.exit(f"error: output={args.output} but these samples' content presets define no " f"miniaod block: {missing[:5]}")
        if args.backend == "crab" and args.output == "both":
            print(" NOTE: two EDM output modules in one CRAB task is not yet verified here. " "If CRAB refuses it, run two tasks with --output ntuple and --output miniaod.")

    if args.backend == "crab":
        cfgs, task, base = crabBackend.prepare(sel, args.task, unitsPerJob=args.filesPerJob, maxMemoryMB=args.memoryMB, output=args.output, assumeYes=args.yes, base=args.outputBase)
        print(f"  wrote {len(cfgs)} crab config(s) under {taskDir(task, create=False)}")
        print(f"  output goes to {base}/ntuples/{task}")
        crabBackend.submit(cfgs, dryRun=args.dryRun, taskName=task, base=base)
    else:
        fileLists = {}
        for s in sel:
            lfns = das.listFiles(s["dataset"], s["dasInstance"], refresh=args.refresh)
            if args.maxFiles:
                lfns = lfns[: args.maxFiles]
            fileLists[s["name"]] = lfns
            print(f"  {s['name']:<48} {len(lfns):>5} file(s)")
        d, nJobs, task, base = condorBackend.prepare(sel, args.task, fileLists, filesPerJob=args.filesPerJob, memoryMB=args.memoryMB, output=args.output, assumeYes=args.yes, base=args.outputBase)
        print(f"  wrote {nJobs} job(s) under {d}")
        print(f"  output goes to {base}/ntuples/{task}")
        condorBackend.submit(task, dryRun=args.dryRun, base=base)


def _cmdSelect(args):
    """Apply an event-level selection to ntuples and write ntuples with the same branches."""
    sel = _pick(args)
    outBase = args.outputBase or loadSites()["stageoutBase"].rstrip("/")
    print(f"task '{args.task}' : {len(sel)} sample(s), selection={args.selection}")

    fileLists = {}
    for s in sel:
        inputs = selectBackend.findInputs(args.inputTask, s["name"], args.inputBase)
        if not inputs:
            print(f"  {s['name']:<44} no input ntuples found, skipping")
            continue
        fileLists[s["name"]] = inputs
    if not fileLists:
        sys.exit("no input ntuples found for any selected sample")

    ## One resolved selection per era, since thresholds differ by era
    eras = sorted({s["era"] for s in sel if s["name"] in fileLists})
    resolvedSelections = {e: resolveSelection(args.selection, era=e) for e in eras}

    if args.backend == "local":
        flows = {}
        for s in sel:
            if s["name"] not in fileLists:
                continue
            outDir = os.path.join(paths.SELECTION_DIR, "out", args.task, s["name"])
            flow = applySelection(fileLists[s["name"]], resolvedSelections[s["era"]],
                                  os.path.join(outDir, f"{s['name']}_selected.root"), writeSteps=args.cutflow)
            flows[s["name"]] = flow
            print(f"  {s['name']:<44} {flow[0]['kept']:>8,} -> {flow[-1]['kept']:>8,}  ({100 * flow[-1]['cumulative']:.1f}%)")
        selectBackend.writeCutflow(paths.SELECTION_DIR, args.task, args.selection, flows)
        print(f"  cutflow written under {os.path.join(paths.SELECTION_DIR, 'out', args.task)}")
        return

    samples = [s for s in sel if s["name"] in fileLists]
    d, nJobs = selectBatch.prepare(samples, args.task, fileLists, resolvedSelections,
                                   filesPerJob=args.filesPerJob, base=args.outputBase)
    print(f"  wrote {nJobs} job(s) under {d}")
    print(f"  output goes to {(args.outputBase or loadSites()['stageoutBase']).rstrip('/')}/selected/{args.task}")
    selectBatch.submit(args.task, dryRun=args.dryRun)


def _cmdNorm(args):
    """Measure a sample's generator sums over a complete production and store them for normalization."""
    sel = _pick(args)
    for s in sel:
        dasEvents = None
        if not args.noDas:
            try:
                dasEvents = das.datasetSummary(s["dataset"], s["dasInstance"])["nevents"]
            except das.DasError as e:
                print(f"  warning: could not ask DAS for {s['name']}: {e}")

        ## Without a production to measure, the DAS count alone is still worth recording
        measured = None
        if args.inputTask:
            inputs = selectBackend.findInputs(args.inputTask, s["name"], args.inputBase)
            if inputs:
                measured = normalization.measure(inputs)
            else:
                print(f"  {s['name']:<44} no ntuples found in task '{args.inputTask}'")

        entry = normalization.record(s["name"], measured, dasEvents,
                                     source=f"production task '{args.inputTask}'" if args.inputTask else "DAS")
        das_ = f"{entry.get('dasEvents', 0):>10,} in DAS" if entry.get("dasEvents") else "  DAS unknown"
        if "sumGenWeight" in entry:
            flag = "" if entry.get("complete") is not False else "   INCOMPLETE, do not normalize with this"
            print(f"  {s['name']:<44} {das_}   measured {entry['nEvents']:,}   sumw {entry['sumGenWeight']:.6g}{flag}")
        else:
            print(f"  {s['name']:<44} {das_}   sumw not measured yet")


def _cmdCutflow(args):
    """Print the cutflow table recorded by a select task."""
    selectBackend.printCutflow(paths.SELECTION_DIR, args.task)


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
        schedd = info.get("schedd")
        cmd = ["condor_q", "-nobatch"] + (["-name", schedd] if schedd else []) + ([str(cluster)] if cluster else [])
        if not cluster:
            print("\n(no cluster id recorded; showing every job you have queued)")
        for retry in info.get("retries", []):
            print(f"retry {retry['retry']}: {retry['nJobs']} job(s) at {retry.get('submittedAt')}, logs in {retry['logDir']}")
        try:
            runTool(cmd)
        except OSError as e:
            print(f"\ncould not run condor_q: {e}")


def _cmdResubmit(args):
    """Resubmit only the jobs of a task whose outputs never reached EOS."""
    d = taskDir(args.task, create=False)
    rec = os.path.join(d, "task.json")
    if not os.path.exists(rec):
        sys.exit(f"no task '{args.task}' under {paths.JOBS_DIR}")
    with open(rec) as f:
        info = json.load(f)

    print(f"task     {info.get('task')}  ({info.get('backend')}, output={info.get('output')})")
    print(f"output   {info.get('outLFNDirBase') or info.get('outDirBase')}")

    if info.get("backend") == "crab":
        # CRAB knows which of its own jobs failed, and writes their output to the same place.
        n = crabBackend.resubmit(args.task, dryRun=args.dryRun)
        print(f"  asked crab to resubmit failed jobs in {n} project(s)")
        return

    missing, nPresent, nExpected = condorBackend.missingJobs(args.task)
    print(f"outputs  {nPresent}/{nExpected} present on EOS")
    if not missing:
        print("  nothing to resubmit")
        return
    print(f"missing  {len(missing)} job(s):")
    for row in missing[:20]:
        sampleName, index = row.split(",")[0], row.split(",")[1]
        print(f"           {sampleName}  job {index}")
    if len(missing) > 20:
        print(f"           ... and {len(missing) - 20} more")

    # A job still on the queue has not failed, and running it again would write the same output twice.
    queued = _queuedJobs(info)
    if queued:
        print(f"  {queued} job(s) from this task are still queued or running.")
        if not args.yes:
            sys.exit("  refusing to resubmit while they run. Wait, or pass --yes to submit anyway.")

    n, nJobs, code = condorBackend.resubmit(args.task, dryRun=args.dryRun)
    if code == 0 and not args.dryRun:
        print(f"  retry {n} submitted: {nJobs} job(s), logs in logs/retry{n}, output to the same directory")
    elif code != 0:
        sys.exit(f"  condor_submit failed with code {code}")


def _queuedJobs(info):
    """How many of this task's jobs are still on the queue, or 0 if that cannot be determined."""
    cluster = info.get("condorCluster")
    if not cluster:
        return 0
    cmd = ["condor_q"] + (["-name", info["schedd"]] if info.get("schedd") else []) + [str(cluster), "-af", "ClusterId"]
    for retry in info.get("retries", []):
        if retry.get("condorCluster"):
            cmd.insert(-2, str(retry["condorCluster"]))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return 0
    return len([line for line in r.stdout.split() if line.strip()]) if r.returncode == 0 else 0


def _cmdCheck(args):
    """Offline validation of every config file."""
    problems = []
    cat = loadCatalog()
    print(f"catalog : {len(cat)} samples in " f"{len({s.get('family') for s in cat})} families")

    ## Every preset resolves within its own era set, for MC and for data
    groups = listPresets()
    nOk = nTried = 0
    byEra = {}
    for group, names in groups.items():
        if group not in ("run2", "run3"):
            continue
        era = "2018" if group == "run2" else "Summer24"
        byEra[group] = set(names)
        for p in names:
            nTried += 1
            try:
                resolveContent(p, isMC=True, era=era)
                resolveContent(p, isMC=False, era=era)
                nOk += 1
            except Exception as e:                                    # noqa: BLE001
                problems.append(f"content preset '{group}/{p}': {e}")
    print(f"content presets: {nOk}/{nTried} resolve for both MC and data")

    problems += validateEraCopies()

    for s in cat:
        group = eraGroup(s["era"])
        if s["content"] not in byEra.get(group, set()):
            problems.append(f"sample '{s['name']}' is {s['era']} ({group}) but wants content preset '{s['content']}', which that era does not define")
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

    ## A sample cannot be normalized without its full-dataset generator count, so record it when the sample is added
    noDas, noSumw = normalization.missingSums([s["name"] for s in cat])
    if noDas:
        problems.append(f"{len(noDas)} sample(s) have no DAS event count recorded; run 'kamui norm' for them. First few: {noDas[:3]}")
    if noSumw:
        print(f"generator sums: {len(cat) - len(noSumw)}/{len(cat)} samples have a weight sum measured")

    sites = loadSites()
    for k in ("eosRedirector", "sourceRedirector", "stageoutBase", "crabStageoutBase", "crabStorageSite"):
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
    if st["n"] and st["newestDays"] is not None:
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
    q.add_argument("--era", help="Era whose content set to resolve against (default: Summer24)")
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
    q.add_argument("--maxFiles", type=int, help="Hard cap on files copied")
    q.add_argument("--dry-run", dest="dryRun", action="store_true", help="Print what would be copied, copy nothing")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdStage)

    q = sub.add_parser("submit", help="Produce ntuples", description=_cmdSubmit.__doc__)
    _addSelection(q)
    q.add_argument("--task", required=True, help="Task name; also the EOS output subdirectory")
    q.add_argument("--backend", choices=["condor", "crab"], default="condor", help="Where the jobs run (default: condor; crab for large productions)")
    q.add_argument("--content", help="Override the per-sample content preset")
    q.add_argument("--output", choices=["ntuple", "miniaod", "both"], default="ntuple", help="What each job writes (default: ntuple)")
    q.add_argument("--filesPerJob", type=int, help="Input files per job, overriding any per-sample unitsPerJob (default: 5)")
    q.add_argument("--maxFiles", type=int, help="Use at most this many input files per sample")
    q.add_argument("--memoryMB", type=int, default=2500, help="Memory request per job in MB (default: 2500)")
    q.add_argument("--dry-run", dest="dryRun", action="store_true", help="Write the job area, submit nothing")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.add_argument("--yes", action="store_true", help="Overwrite an existing job area without asking")
    q.add_argument("--outputBase", help="Write output under this EOS path instead of the site default")
    q.set_defaults(func=_cmdSubmit)

    q = sub.add_parser("select", help="Apply an event selection to ntuples", description=_cmdSelect.__doc__)
    _addSelection(q)
    q.add_argument("--selection", required=True, help="Selection config name, e.g. run2Lepton")
    q.add_argument("--task", required=True, help="Name for this selection pass")
    q.add_argument("--inputTask", required=True, help="The ntuple production task to read from")
    q.add_argument("--inputBase", help="EOS base holding the input ntuples (default: the site stageout base)")
    q.add_argument("--outputBase", help="Where to write the selected ntuples")
    q.add_argument("--cutflow", action="store_true", help="Also write one ntuple per cut, for inspection (local only)")
    q.add_argument("--backend", choices=["local", "condor"], default="local", help="Where the selection runs (default: local, which is seconds for a small pass)")
    q.add_argument("--filesPerJob", type=int, help="Input files per job on condor (default: 5)")
    q.add_argument("--dry-run", dest="dryRun", action="store_true", help="Write the job area, submit nothing")
    q.set_defaults(func=_cmdSelect)

    q = sub.add_parser("norm", help="Measure and store generator sums for normalization", description=_cmdNorm.__doc__)
    _addSelection(q)
    q.add_argument("--inputTask", help="A complete production task to measure the weight sum over; omit to record the DAS count alone")
    q.add_argument("--inputBase", help="EOS base holding the ntuples (default: the site stageout base)")
    q.add_argument("--noDas", action="store_true", help="Skip the DAS cross-check of the event count")
    q.set_defaults(func=_cmdNorm)

    q = sub.add_parser("cutflow", help="Print the cutflow from a select task", description=_cmdCutflow.__doc__)
    q.add_argument("--task", required=True, help="Select task name")
    q.set_defaults(func=_cmdCutflow)

    q = sub.add_parser("status", help="Status of a submitted task", description=_cmdStatus.__doc__)
    q.add_argument("--task", required=True, help="Task name under ntupleProduction/jobs/")
    q.set_defaults(func=_cmdStatus)

    q = sub.add_parser("resubmit", help="Resubmit only a task's failed jobs", description=_cmdResubmit.__doc__)
    q.add_argument("--task", required=True, help="The task to retry")
    q.add_argument("--dry-run", dest="dryRun", action="store_true", help="Report what would be resubmitted, submit nothing")
    q.add_argument("--yes", action="store_true", help="Resubmit even while jobs from this task are still queued")
    q.set_defaults(func=_cmdResubmit)

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
    except (KeyError, FileNotFoundError, PermissionError, ValueError, das.DasError) as e:
        # Config and DAS problems are user errors - say what is wrong and stop.
        # Anything else still raises.
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    sys.exit(main())
