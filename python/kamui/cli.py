#!/usr/bin/env python3
"""
Kamui - the CLI for the analysis framework.
See python/kamui/README.md for what each command does and the flags they take.
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
from .configReaders.content import eraGroup, listPresets, listTriggerConfigs, resolveContent, summarize, validateEraCopies, validateTriggers
from .submit import condor as condorBackend, crab as crabBackend
from .select import batch as selectBatch, io as selectBackend, normalization
from .select.engine import applySelection
from .configReaders.selections import listSelections, resolveSelection, selectionEras
from .configReaders.sites import loadSites
from .submit.common import runTool, taskDir

# Sample Selection Helper Functions
## These come first because other functions later on depend on them to work.

def _addSelection(p):
    """
    Gives a sample-related command defined in main() the five sample selection flags.
    Sample convention documented in Kamui/config/samples/README.md
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


## Commands that act on samples, so running them bare has nothing to do.
NEEDS_SELECTION = {"query", "stage", "submit", "select", "norm"}


# Commands!

def _cmdList(args):
    """List available samples. If no selection flags are passed, list all registered samples."""
    sel = _pick(args, required=False)
    if args.datasets:
        for s in sel:
            print(s["dataset"])
        return
    fams = {}
    for s in sel:
        fams.setdefault(s.get("family", "?"), []).append(s)
    ## Widths from the data, so a long preset name does not push the tags out of line
    wName = max([len(s["name"]) for s in sel] + [6])
    wEra = max([len(s.get("era", "-")) for s in sel] + [3])
    wContent = max([len(s["content"]) for s in sel] + [7])
    for fam in sorted(fams):
        n = len(fams[fam])
        print(f"\n{fam}  ({n} sample{'' if n == 1 else 's'})")
        print(f"  {'Sample':<{wName}}  {'Era':<{wEra}}  {'Content':<{wContent}}  Tags")
        for s in sorted(fams[fam], key=lambda x: x["name"]):
            print(f"  {s['name']:<{wName}}  {s.get('era','-'):<{wEra}}  {s['content']:<{wContent}}  {','.join(s['tags'])}")
    print(f"\n{len(sel)} sample{'' if len(sel) == 1 else 's'} total")


def _cmdContent(args):
    """Show what a content preset writes out. If no preset flags are passed, lists all the presets available."""
    if not args.preset:
        for group, names in listPresets().items():
            print(f"{group or 'content'}: " + ", ".join(names))
        return
    resolved = resolveContent(args.preset, isMC=not args.data, era=args.era or "Summer24")
    print(f"{args.preset}  (isMC={not args.data})")
    print(summarize(resolved))
    nvar = sum(len(c.get("variables", c.get("extVariables", {}))) for c in resolved["collections"].values())
    ncol = len(resolved["collections"])
    print(f"\n  {ncol} collection{'' if ncol == 1 else 's'}, {nvar} variable{'' if nvar == 1 else 's'}")
    skim = resolved["skim"]
    if skim:
        npath = len(skim.get("hltPaths", []))
        print(f"  skim: {skim['triggers']} ({npath} path{'' if npath == 1 else 's'}, "
              f"mode {skim.get('mode', 'any')}, process {skim.get('process', 'HLT')})")
    if args.write:
        with open(args.write, "w") as f:
            json.dump(resolved, f, indent=2)
        print(f"  wrote {args.write}")


def _cmdQuery(args):
    """Ask DAS how many files, events and GB each selected sample holds. Needs cmsenv and a grid proxy."""
    sel = _pick(args)
    totF = totE = totS = 0
    w = max([len(s["name"]) for s in sel] + [len("Sample")])
    print(f"{'Sample':<{w}} {'Files':>7} {'Events':>12} {'Size/GB':>9}")
    missing = []
    for s in sel:
        info = das.datasetSummary(s["dataset"], s["dasInstance"], refresh=args.refresh)
        ## DAS answering with nothing means it does not know the name, which usually means a
        ## typo in the config. Printing zeros there would read as a dataset that is merely empty.
        if not info["found"]:
            print(f"{s['name']:<{w}} {'-':>7} {'-':>12} {'-':>9}   Not found in DAS")
            missing.append(s["name"])
            continue
        print(f"{s['name']:<{w}} {info['nfiles']:>7} {info['nevents']:>12,} {info['sizeGB']:>9.1f}")
        totF += info["nfiles"]; totE += info["nevents"]; totS += info["sizeGB"]
    print(f"{'TOTAL':<{w}} {totF:>7} {totE:>12,} {totS:>9.1f}")
    if missing:
        shown = ", ".join(missing[:5]) + (", ..." if len(missing) > 5 else "")
        print(f"\n{len(missing)} sample{'' if len(missing) == 1 else 's'} not found in DAS under the instance they name: {shown}")
        return 1
    return 0


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
    """Build a job area for the selected samples and submit them. Use --dryRun first for testing."""
    sel = _pick(args)
    if args.filesPerJob is not None and args.filesPerJob < 1:
        sys.exit(f"--filesPerJob must be at least 1, got {args.filesPerJob}")
    if args.maxFiles is not None and args.maxFiles < 1:
        sys.exit(f"--maxFiles must be at least 1, got {args.maxFiles}")
    if args.content:                       # override the per-sample preset
        for s in sel:
            s["content"] = args.content
    print(f"Task '{args.task}' : {len(sel)} sample(s), backend={args.backend}")

    if args.backend == "crab":
        cfgs, task, base = crabBackend.prepare(sel, args.task, unitsPerJob=args.filesPerJob, maxMemoryMB=args.memoryMB, assumeYes=args.overwrite, base=args.outputBase)
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
        d, nJobs, task, base = condorBackend.prepare(sel, args.task, fileLists, filesPerJob=args.filesPerJob, memoryMB=args.memoryMB, assumeYes=args.overwrite, base=args.outputBase)
        print(f"  wrote {nJobs} job(s) under {d}")
        print(f"  output goes to {base}/ntuples/{task}")
        condorBackend.submit(task, dryRun=args.dryRun, base=base)


def _cmdSelect(args):
    """Apply an event-level selection to ntuples and write ntuples with the same branches."""
    sel = _pick(args)
    outBase = args.outputBase or loadSites()["stageoutBase"].rstrip("/")
    print(f"Task '{args.task}' : {len(sel)} sample(s), selection={args.selection}")

    fileLists = {}
    for s in sel:
        inputs = selectBackend.findInputs(args.inputTask, s["name"], args.inputBase)
        if not inputs:
            print(f"  {s['name']:<44} no input ntuples found, skipping")
            continue
        fileLists[s["name"]] = inputs
    if not fileLists:
        sys.exit("No input ntuples found for any selected sample")

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
                                  os.path.join(outDir, f"{s['name']}_selected.root"))
            flows[s["name"]] = selectBackend.withGenerated(flow, normalization.generatedEvents(s["name"]))
            print(f"  {s['name']:<44} {flow[0]['kept']:>8,} -> {flow[-1]['kept']:>8,}  ({100 * flow[-1]['kept'] / flow[0]['kept'] if flow[0]['kept'] else 0:.1f}%)")
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
    """Record the generator weight sum every yield is divided by. MC only, since data has no generator weights."""
    sel = _pick(args)
    data = [s["name"] for s in sel if not s.get("isMC")]
    sel = [s for s in sel if s.get("isMC")]
    if data:
        print(f"  Skipping {len(data)} data sample(s); a generator weight sum has no meaning there")
    if not sel:
        sys.exit("No MC samples matched the selection")

    ## The sums come from the sample's central NanoAOD, which covers the whole dataset and owes
    ## nothing to anything we produced. DAS cannot serve them: a weight sum is a property of the
    ## event payload, so it is recorded nowhere central except inside the files themselves.
    for s in sel:
        nano = das.nanoSibling(s["dataset"], s["dasInstance"], refresh=args.refresh)
        if not nano:
            print(f"  {s['name']:<44} No central NanoAOD sibling found")
            continue
        try:
            measured = normalization.measureFromNano(das.listFiles(nano, s["dasInstance"], refresh=args.refresh))
        except (RuntimeError, das.DasError) as e:
            print(f"  {s['name']:<44} {e}")
            continue
        entry = normalization.record(s["name"], measured, measured["genEvents"], write=args.write)
        print(f"  {s['name']:<44} {entry['genEvents']:>10,} events   sumw {entry['sumGenWeight']:.6g}")
    if not args.write:
        print("  Nothing written. Pass --write to store these in config/normalizations/generatorSums.json")
    return 0


def _cmdCutflow(args):
    """Print the cutflow table recorded by a select task."""
    selectBackend.printCutflow(paths.SELECTION_DIR, args.task)


def _cmdStatus(args):
    """Show the current tasks status and configuration."""
    d = taskDir(args.task, create=False)
    rec = os.path.join(d, "task.json")
    if not os.path.exists(rec):
        sys.exit(f"No task '{args.task}' under {paths.JOBS_DIR}")
    with open(rec) as f:
        info = json.load(f)

    # Print the few lines that matter; the record embeds every resolved preset and runs to tens of kB.
    prov = info.get("provenance", {})
    print(f"Task     {info.get('task')}  ({info.get('backend')})")
    print(f"Samples  {len(info.get('samples', []))}, content {', '.join(info.get('content') or sorted({c for c in [d.get('content') for d in info.get('sampleDetails', [])] if c}))}")
    if info.get("nJobs") is not None:
        print(f"Jobs     {info['nJobs']}")
    if prov:
        dirty = " (dirty tree)" if prov.get("dirty") else ""
        print(f"From     {str(prov.get('commit'))[:8]} on {prov.get('branch')}{dirty}, by {prov.get('submittedBy')} at {prov.get('submittedAt')}")
    print(f"Output   {info.get('outLFNDirBase') or info.get('outDirBase')}")
    print(f"Record   {rec}")

    if info.get("backend") == "crab":
        crabBackend.status(args.task)
    else:
        cluster = info.get("condorCluster")
        schedd = info.get("schedd")
        cmd = ["condor_q", "-nobatch"] + (["-name", schedd] if schedd else []) + ([str(cluster)] if cluster else [])
        if not cluster:
            print("\n(no cluster id recorded; showing every job you have queued)")
        for retry in info.get("retries", []):
            print(f"Retry {retry['retry']}: {retry['nJobs']} job(s) at {retry.get('submittedAt')}, logs in {retry['logDir']}")
        try:
            runTool(cmd)
        except OSError as e:
            print(f"\ncould not run condor_q: {e}")


def _cmdResubmit(args):
    """Resubmit jobs that did not write to output paths."""
    d = taskDir(args.task, create=False)
    rec = os.path.join(d, "task.json")
    if not os.path.exists(rec):
        sys.exit(f"No task '{args.task}' under {paths.JOBS_DIR}")
    with open(rec) as f:
        info = json.load(f)

    print(f"Task     {info.get('task')}  ({info.get('backend')})")
    print(f"Output   {info.get('outLFNDirBase') or info.get('outDirBase')}")

    if info.get("backend") == "crab":
        # CRAB knows which of its own jobs failed, and writes their output to the same place.
        n = crabBackend.resubmit(args.task, dryRun=args.dryRun)
        print(f"  asked crab to resubmit failed jobs in {n} project(s)")
        return

    missing, nPresent, nExpected = condorBackend.missingJobs(args.task)
    print(f"Outputs  {nPresent}/{nExpected} present on EOS")
    if not missing:
        print("  nothing to resubmit")
        return
    print(f"Missing  {len(missing)} job(s):")
    for row in missing[:20]:
        sampleName, index = row.split(",")[0], row.split(",")[1]
        print(f"           {sampleName}  job {index}")
    if len(missing) > 20:
        print(f"           ... and {len(missing) - 20} more")

    # A job still on the queue has not failed, and running it again would write the same output twice.
    queued = _queuedJobs(info)
    if queued:
        print(f"  {queued} job(s) from this task are still queued or running.")
        if not args.forceResubmit:
            sys.exit("  refusing to resubmit while they run. Wait, or pass --forceResubmit to submit anyway.")

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
        r = runTool(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return 0
    return len([line for line in r.stdout.split() if line.strip()]) if r.returncode == 0 else 0


def _cmdCheck(args):
    """Offline validation of every config file."""
    problems = []
    ## Each entry is one named check, so the report says what was verified rather than only a count.
    ## A check is "warn" when it is incomplete rather than wrong, which must not fail the run.
    report = []

    def note(label, state, text):
        report.append((label, state, text))

    cat = loadCatalog()
    bad = len([s for s in cat if not s["dataset"].startswith("/") or s["dataset"].count("/") != 3])
    dupes = len(cat) - len({s["name"] for s in cat})
    for s in cat:
        if not s["dataset"].startswith("/") or s["dataset"].count("/") != 3:
            problems.append(f"sample '{s['name']}' has a malformed dataset path")
    if dupes:
        problems.append(f"{dupes} duplicate sample name(s)")
    note("Catalog", "pass" if not bad and not dupes else "fail",
         f"Every sample is listed once and is well-formatted ({len(cat)} samples in {len({s.get('family') for s in cat})} families)")

    ## Resolving a preset means expanding its include chain, dropping the collections that do not
    ## apply, and naming a CMSSW plugin for every one that does. That is what a job receives.
    groups = listPresets()
    nOk = nTried = 0
    byEra = {}
    for group, names in groups.items():
        if group not in ("run2", "run3"):
            continue
        era = "2018" if group == "run2" else "Summer24"
        byEra[group] = set(names)
        for preset in names:
            nTried += 1
            try:
                resolveContent(preset, isMC=True, era=era)
                resolveContent(preset, isMC=False, era=era)
                nOk += 1
            except Exception as e:                                    # noqa: BLE001
                problems.append(f"content preset '{group}/{preset}': {e}")
    note("Content presets", "pass" if nOk == nTried else "fail", f"Validated the format of each preset ({nOk}/{nTried})")

    ## Resolving a selection means collapsing every era-keyed threshold, trigger list and flag list
    ## to one value, and checking every cut type and quantity name the config uses.
    nSel = nSelTried = 0
    for name in listSelections():
        for era in (selectionEras(name) or [None]):
            nSelTried += 1
            try:
                resolveSelection(name, era=era)
                nSel += 1
            except Exception as e:                                    # noqa: BLE001
                problems.append(f"selection '{name}' for era '{era}': {e}")
    note("Selections", "pass" if nSel == nSelTried else "fail", f"Validated the format of every cut ({nSel}/{nSelTried})")

    nTrig = len(listTriggerConfigs())
    trigProblems = validateTriggers()
    problems += trigProblems
    note("Triggers", "pass" if not trigProblems else "fail", f"Every trigger file is parseable ({nTrig - len(trigProblems)}/{nTrig})")

    eraProblems = validateEraCopies()
    problems += eraProblems
    note("Era isolation", "pass" if not eraProblems else "fail", "Run 2 and Run 3 keep separate copies of content files")

    for s in cat:
        if s["content"] not in byEra.get(eraGroup(s["era"]), set()):
            problems.append(f"sample '{s['name']}' is {s['era']} ({eraGroup(s['era'])}) but wants content preset '{s['content']}', which that era does not define")

    ## foundations/ is a layer, not just a folder: nothing in it may import from above
    layerProblems = []
    foundDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foundations")
    for f in sorted(x for x in os.listdir(foundDir) if x.endswith(".py")):
        for line in open(os.path.join(foundDir, f)):
            if line.startswith("from ..") or (line.startswith("from .") and not line.startswith("from ." + "foundations")):
                layerProblems.append(f"foundations/{f} imports from above the foundation layer: {line.strip()}")
    problems += layerProblems
    note("Layering", "pass" if not layerProblems else "fail", "foundations/ does not import from the rest of the framework")


    ## configReaders/ owns the config files: nothing outside it may open one directly
    accessProblems = []
    pkgDir = os.path.dirname(os.path.abspath(__file__))
    for root, _, files in os.walk(pkgDir):
        if "configReaders" in root or "__pycache__" in root:
            continue
        for f in sorted(x for x in files if x.endswith(".py")):
            for line in open(os.path.join(root, f)):
                if any("paths." + d in line for d in ("CONFIG_DIR", "SAMPLES_DIR", "CONTENT_DIR", "TRIGGERS_DIR", "SITES_FILE")):
                    accessProblems.append(f"{os.path.relpath(os.path.join(root, f), pkgDir)} reads a config directory directly; that belongs in configReaders/")
    problems += accessProblems
    note("Config access", "pass" if not accessProblems else "fail", "configReaders/ is the only folder containing config access scripts")

    ## A sample cannot be normalized without its full-dataset generator sum
    noCount, noSumw = normalization.missingSums([s["name"] for s in cat])
    if noCount:
        problems.append(f"{len(noCount)} sample(s) have no generated event count recorded; run 'kamui norm --write' for them. First few: {noCount[:3]}")
    note("Generator sums", "pass" if not noSumw else "warn", f"Samples that know their total generator weight ({len(cat) - len(noSumw)}/{len(cat)})")

    sites = loadSites()
    missingKeys = [k for k in ("eosRedirector", "sourceRedirector", "stageoutBase", "crabStageoutBase", "crabStorageSite") if k not in sites]
    missingCfg = [f for f in ("kamuiNtuple_cfg.py", "kamuiTables.py") if not os.path.exists(os.path.join(paths.CMSSW_DIR, f))]
    for k in missingKeys:
        problems.append(f"sites.json is missing '{k}'")
    for f in missingCfg:
        problems.append(f"missing cmssw/{f}")
    note("Sites and CMSSW", "pass" if not missingKeys and not missingCfg else "fail", "Validated sites.json and the CMSSW job script configurations")

    MARK = {"pass": "\u2705", "fail": "\u274c", "warn": "\u26a0\ufe0f "}
    width = max(len(label) for label, _, _ in report)
    for label, state, text in report:
        print(f"{MARK[state]}  {label:<{width}}  {text}")

    if problems:
        print("\nPROBLEMS:")
        for problem in problems:
            print("  " + problem)
        return 1
    print("\nAll configs OK")
    return 0


def _cmdCache(args):
    """Inspect, prune or clear the on-disk cache of DAS responses."""
    if args.clear:
        das.clearCache()
        print("DAS cache cleared")
        return
    if args.prune:
        print(f"Pruned {das.pruneCache()} expired entry(s)")
    st = das.cacheStats()
    print(f"{st['n']} cached DAS response{'' if st['n'] == 1 else 's'}, {st['bytes'] / 1e6:.1f} MB in {st['dir']}")
    if st["n"] and st["newestDays"] is not None:
        print(f"  age      {st['newestDays']:.1f} to {st['oldestDays']:.1f} days")
        print(f"  expired  {st['nStale']} (older than {das.CACHE_MAX_AGE_DAYS} days, ignored on read)")


# Parser!

## The usage line repeats what the help below it already shows, so it is dropped everywhere.
class _Formatter(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        return

    def _format_action(self, action):
        text = super()._format_action(action)
        ## The subparsers action prints an empty metavar line above the command list.
        if action.nargs == argparse.PARSER:
            text = "\n".join(text.split("\n")[1:])
        return text


## A command run with nothing to act on gets the help rather than an error from deep inside the command.
class _CommandParser(argparse.ArgumentParser):
    def error(self, message):
        print(f"Hey, you can't run this command alone! {message[0].upper()}{message[1:]}\n")
        self.print_help()
        sys.exit(2)


def _titles(q):
    q._positionals.title = "Positional arguments"
    q._optionals.title = "Optional arguments"
    return q


## -h still works; it is hidden because a reader who got here already found it.
def _addCmd(sub, name, help, description):
    q = sub.add_parser(name, help=help, description=description, formatter_class=_Formatter, add_help=False)
    q.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    return _titles(q)


def main(argv=None):
    p = argparse.ArgumentParser(prog="kamui", description=__doc__, formatter_class=_Formatter, add_help=False)
    p.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    p.add_argument("--noBanner", action="store_true", help="Skip the startup banner")
    _titles(p)
    sub = p.add_subparsers(dest="cmd", metavar="", parser_class=_CommandParser)

    q = _addCmd(sub, "list", help="Show all available samples", description=_cmdList.__doc__)
    _addSelection(q)
    q.add_argument("--datasets", action="store_true", help="Print DAS paths only")
    q.set_defaults(func=_cmdList)

    q = _addCmd(sub, "content", help="Show presets declaring what we save in ntuples", description=_cmdContent.__doc__)
    q.add_argument("preset", nargs="?", help="Preset name; omit argument to list all of them")
    q.add_argument("--data", action="store_true", help="Resolve as data (drops mcOnly collections)")
    q.add_argument("--era", help="Era configuration we use (default: Summer24)")
    q.add_argument("--write", help="Write the resolved JSON here")
    q.set_defaults(func=_cmdContent)

    q = _addCmd(sub, "query", help="Query DAS for how many files, events and GB each selected sample holds", description=_cmdQuery.__doc__)
    _addSelection(q)
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdQuery)

    q = _addCmd(sub, "find", help="Unrestricted DAS dataset search", description=_cmdFind.__doc__)
    q.add_argument("pattern", help="DAS wildcard, e.g. '/*HAHM*/*/MINIAODSIM'")
    q.add_argument("--instance", default="prod/global", help="prod/global for official datasets, prod/phys03 for USER ones")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdFind)

    q = _addCmd(sub, "stage", help="Copy raw MiniAOD to EOS", description=_cmdStage.__doc__)
    _addSelection(q)
    q.add_argument("--maxFiles", type=int, help="Hard cap on files copied")
    q.add_argument("--dryRun", action="store_true", help="Print what would be copied, but copy nothing")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdStage)

    q = _addCmd(sub, "submit", help="Produce ntuples by submitting to condor or CRAB", description=_cmdSubmit.__doc__)
    _addSelection(q)
    q.add_argument("--task", required=True, help="Task name; also the EOS output subdirectory")
    q.add_argument("--backend", choices=["condor", "crab"], default="condor", help="Where the jobs run (default: condor)")
    q.add_argument("--content", help="Override the per-sample content preset")
    q.add_argument("--filesPerJob", type=int, help="Input files per job, overriding any per-sample unitsPerJob (default: 5)")
    q.add_argument("--maxFiles", type=int, help="Use at most this many input files per sample")
    q.add_argument("--memoryMB", type=int, default=2500, help="Memory request per job in MB (default: 2500)")
    q.add_argument("--dryRun", action="store_true", help="Write the job area, submit nothing")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.add_argument("--overwrite", action="store_true", help="Overwrite an existing job area without asking")
    q.add_argument("--outputBase", help="Write output under this EOS path instead of the site default")
    q.set_defaults(func=_cmdSubmit)

    q = _addCmd(sub, "resubmit", help="Rerun failed jobs", description=_cmdResubmit.__doc__)
    q.add_argument("--task", required=True, help="The task to retry")
    q.add_argument("--dryRun", action="store_true", help="Report what would be resubmitted, submit nothing")
    q.add_argument("--forceResubmit", action="store_true", help="Resubmit even while jobs from this task are still queued")
    q.set_defaults(func=_cmdResubmit)

    q = _addCmd(sub, "status", help="Status of a submitted task", description=_cmdStatus.__doc__)
    q.add_argument("--task", required=True, help="Task name under ntupleProduction/jobs/")
    q.set_defaults(func=_cmdStatus)

    q = _addCmd(sub, "select", help="Apply an event selection to ntuples", description=_cmdSelect.__doc__)
    _addSelection(q)
    q.add_argument("--selection", required=True, help="Selection config name, e.g. run2Lepton")
    q.add_argument("--task", required=True, help="Name for this selection pass")
    q.add_argument("--inputTask", required=True, help="The ntuple production task to read from")
    q.add_argument("--inputBase", help="EOS base holding the input ntuples (default: the site stageout base)")
    q.add_argument("--outputBase", help="Where to write the selected ntuples")
    q.add_argument("--backend", choices=["local", "condor"], default="local", help="Where the selection runs (default: local)")
    q.add_argument("--filesPerJob", type=int, help="Input files per job on condor (default: 5)")
    q.add_argument("--dryRun", action="store_true", help="Write the job area, submit nothing")
    q.set_defaults(func=_cmdSelect)

    q = _addCmd(sub, "cutflow", help="Print the cutflow for a given task", description=_cmdCutflow.__doc__)
    q.add_argument("--task", required=True, help="Select task name")
    q.set_defaults(func=_cmdCutflow)

    q = _addCmd(sub, "norm", help="Measure and store weights for normalization", description=_cmdNorm.__doc__)
    _addSelection(q)
    q.add_argument("--write", action="store_true", help="Store the sums in config/normalizations/generatorSums.json")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdNorm)

    q = _addCmd(sub, "check", help="Validate configuration files", description=_cmdCheck.__doc__)
    q.set_defaults(func=_cmdCheck)

    q = _addCmd(sub, "cache", help="Inspect or clear the DAS cache", description=_cmdCache.__doc__)
    q.add_argument("--clear", action="store_true", help="Delete every cached response")
    q.add_argument("--prune", action="store_true", help="Delete only the expired entries, keeping the rest")
    q.set_defaults(func=_cmdCache)

    ## The banner is an orientation aid, so it appears with the help and stays out of the way otherwise.
    given = list(argv if argv is not None else sys.argv[1:])
    printBanner(enabled=(not given or "-h" in given or "--help" in given) and "--noBanner" not in given)
    args = p.parse_args(argv)
    ## No command at all is a request to see what the commands are.
    if not args.cmd:
        p.print_help()
        return 0
    if args.cmd in NEEDS_SELECTION and not any([args.name, args.family, args.era, args.tag, args.match]):
        print("Hey, you can't run this command alone! Name what it should act on.\n")
        sub.choices[args.cmd].print_help()
        return 2
    try:
        return args.func(args)
    except (KeyError, FileNotFoundError, PermissionError, ValueError, das.DasError) as e:
        # Config and DAS problems are user errors - say what is wrong and stop.
        # Anything else still raises.
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    sys.exit(main())
