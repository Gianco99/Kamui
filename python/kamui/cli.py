#!/usr/bin/env python3
"""
Kamui is the CLI for the analysis framework.
See python/kamui/README.md for what each command does and the flags they take.
"""

# Import Block

## Standard Python imports
import argparse
import importlib.util
import json
import os
import sys

## Kamui modules
from .grid import das, fetch
from .foundations import paths
from .foundations.config import RUN2_ERAS, RUNS, eraGroup
from .helpers.banner import printBanner
from .configReaders.catalog import loadCatalog, select
from .configReaders.content import listCollections, listPresets, listTriggerConfigs, resolveContent, summarize, validateTriggers
from .configReaders.normalizations import validateNormalizations
from .submit import condor as condorBackend, crab as crabBackend
from .select import batch as selectBatch, io as selectBackend, normalization
from .configReaders.requirements import definitionEras, definitionFiles, resolveRequirements
from .configReaders.selections import resolveSelection, runEras, selectionEras, selectionFiles
from .configReaders.sites import loadSites
from .submit.common import outputDir, readTaskRecord, recordedOutputDir, runTool, taskDir

# Sample Selection Helper Functions
## These come first because the commands below use them.

def _addSelection(p):
    """Gives a sample command the five sample selection flags. The sample convention is in config/samples/README.md."""
    p.add_argument("--name", metavar="NAME", action="append", help="Exact sample name")
    p.add_argument("--family", metavar="NAME", help="Family file name, e.g. exoticHiggs4d2024")
    p.add_argument("--era", metavar="NAME", help="Data-taking period, e.g. Summer24")
    p.add_argument("--tag", metavar="NAME", help="Tag from the sample config, e.g. signal")
    p.add_argument("--match", metavar="PATTERN", help="Wildcard on the sample name, e.g. 'ggH*ctau10mm*'")

def _pick(args, required=True):
    """Turns the sample selection flags into a list of samples."""
    cat = loadCatalog()
    ## The catalog raises KeyError for a sample name, family, era or tag it does not know
    try:
        sel = select(cat, names=args.name, family=args.family, era=args.era, tag=args.tag, pattern=args.match)
    except KeyError as e:
        sys.exit(f"Error: {e.args[0]}")
    if required and not sel:
        sys.exit("No samples matched the selection (try `kamui list`)")
    return sel


## Commands that act on samples, so running them bare has nothing to do.
NEEDS_SELECTION = {"query", "stage", "submit", "select", "norm"}


# Config Helper Functions

## Content files check skips while their configuration is unfinished, by run
PARKED_CONTENT = {"run3": {"vertexing"}}


def _runEras(cat=None, sites=None):
    """Every era of each run, as {run: [eras]}: the Run 2 eras, plus every era the catalog, the sites.json global tags and the selections name."""
    cat = loadCatalog() if cat is None else cat
    sites = loadSites() if sites is None else sites
    known = set(RUN2_ERAS) | {s["era"] for s in cat} | set(sites.get("globalTags") or {}) | {e for run in RUNS for e in runEras(run)}
    return {run: sorted(e for e in known if eraGroup(e) == run) for run in RUNS}


def _checkEra(era):
    """Stops on an era neither run knows, since eraGroup reads any name outside RUN2_ERAS as Run 3."""
    known = [e for run in RUNS for e in _runEras()[run]]
    if era not in known:
        sys.exit(f"Error: Unknown era '{era}'. Known eras: {', '.join(known)}")


def _otherRunHint(name, namesByRun, era):
    """For a config missing from the run folder an era reads, the --era to pass when the other run defines it. Empty otherwise."""
    own = eraGroup(era)
    for part in (p.strip() for p in name.split(",")):
        if not part or part in namesByRun.get(own, []):
            continue
        for run in RUNS:
            if run != own and part in namesByRun.get(run, []):
                return f". '{part}' is a {run} config, so pass --era with one of: {', '.join(_runEras()[run])}"
    return ""


## The names come from the table producers a job builds, so the DV quantities DVProducer adds are read from DV_SELECTION_QUANTITIES in ntupleTables.py.
def _branches(resolved):
    """The branches a resolved content writes, as {collection: [names]}. A collection whose CMSSW producer fixes its branches, or that only feeds the vertexer, gets a note."""
    spec = importlib.util.spec_from_file_location("ntupleTables", os.path.join(paths.CMSSW_DIR, "ntupleTables.py"))
    tables = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tables)
    modules, _ = tables.buildTables(resolved)
    out = {}
    for mod in modules.values():
        params = mod.parameterNames_()
        if "name" not in params:
            continue
        cname = mod.name.value()
        ## A table of many objects per event also writes their count
        names = [f"n{cname}"] if "singleton" in params and not mod.singleton.value() else []
        for block in ("variables", "externalVariables"):
            if block in params:
                names += [f"{cname}_{v}" for v in getattr(mod, block).parameterNames_()]
        out[cname] = names
    for cname, c in resolved["collections"].items():
        if cname not in out:
            out[cname] = ["(named by its CMSSW producer)"] if c.get("writesTable", True) else ["(none, the vertexer reads it)"]
    return dict(sorted(out.items()))


def _taskRecord(taskName):
    """The job area and task.json of a production task, or else of a condor selection pass."""
    found = [d for d in (taskDir(taskName, create=False), selectBatch.taskDir(taskName, create=False)) if os.path.isfile(os.path.join(d, "task.json"))]
    if not found:
        ## A local selection pass runs inside kamui itself, so it leaves no jobs behind
        if os.path.isfile(os.path.join(paths.SELECTION_OUT_DIR, taskName, "task.json")):
            sys.exit(f"Task '{taskName}' is a local selection pass, so it has no jobs to follow or retry. ./kamui cutflow --task {taskName} shows what it kept.")
        sys.exit(f"No task '{taskName}' under {paths.JOBS_DIR} or {paths.SELECTION_JOBS_DIR}")
    if len(found) > 1:
        print(f"Task '{taskName}' names both a production task and a selection pass, and this is the production task. The selection pass is under {found[1]}.\n")
    return found[0], readTaskRecord(found[0])


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
    """Show what a content preset or collection file writes out, down to its branch names. If no preset is given, lists all the presets available."""
    if not args.preset:
        for group, names in listPresets().items():
            print(f"{group or 'content'}: " + ", ".join(names))
        return
    _checkEra(args.era)
    try:
        resolved = resolveContent(args.preset, isMC=not args.data, era=args.era)
    except FileNotFoundError as e:
        presets, collections = listPresets(), listCollections()
        sys.exit(f"Error: {e}{_otherRunHint(args.preset, {run: presets.get(run, []) + collections.get(run, []) for run in RUNS}, args.era)}")
    print(f"{args.preset}  (isMC={not args.data}, era {args.era})")
    try:
        branches = _branches(resolved)
    except ImportError as e:
        branches, branchError = None, e
    ## A collection's count is its own branches, leaving out the n<Collection> length branch
    counts = {cname: len([b for b in names if b.startswith(cname + "_")]) for cname, names in (branches or {}).items() if any(b.startswith(cname + "_") for b in names)}
    print(summarize(resolved, counts))
    nvar = sum(counts.get(cname, len(c.get("variables", c.get("extVariables", {})))) for cname, c in resolved["collections"].items())
    ncol = len(resolved["collections"])
    print(f"\n  {ncol} collection{'' if ncol == 1 else 's'}, {nvar} variable{'' if nvar == 1 else 's'}")
    skim = resolved["skim"]
    if skim:
        npath = len(skim.get("hltPaths", []))
        print(f"  skim: {skim['triggers']} ({npath} path{'' if npath == 1 else 's'}, mode {skim.get('mode', 'any')}, process {skim.get('process', 'HLT')})")
    if branches is None:
        print(f"\n  Branch names need the CMSSW environment, so run cmsenv first ({branchError})")
    else:
        print("\n  Branches")
        for cname, names in branches.items():
            print(f"  {cname:<12} {', '.join(names)}")
    if args.write:
        with open(args.write, "w") as f:
            json.dump(resolved, f, indent=2)
        print(f"  Wrote {args.write}")


def _cmdQuery(args):
    """Ask DAS how many files, events and GB each selected sample holds. Needs cmsenv and a grid proxy."""
    sel = _pick(args)
    totF = totE = totS = 0
    w = max([len(s["name"]) for s in sel] + [len("Sample")])
    print(f"{'Sample':<{w}} {'Files':>7} {'Events':>12} {'Size/GB':>9}")
    missing = []
    for s in sel:
        info = das.datasetSummary(s["dataset"], s["dasInstance"], refresh=args.refresh)
        ## An unknown name usually means a config typo, and printing zeros would read as an empty dataset.
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
    """Copy a sample's MiniAOD files to EOS, under <stageoutBase>/<miniaodDir>/<sample>/ from sites.json, to run one job by hand on files at FNAL or prototype a content preset."""
    sites = loadSites()
    if args.maxFiles is not None and args.maxFiles < 1:
        sys.exit(f"--maxFiles must be at least 1, got {args.maxFiles}")
    sel = _pick(args)
    inPlace = failed = 0
    for s in sel:
        print(f"\n=== {s['name']}\n  {s['dataset']}")
        ok, bad = fetch.stage(s, sites, maxFiles=args.maxFiles, dryRun=args.dryRun, refresh=args.refresh)
        inPlace += ok
        failed += bad
    ## A dry run counts each file it would copy, so its total is what a real run would leave on EOS
    print(f"\n{inPlace} file(s) would be in place, nothing copied" if args.dryRun else f"\n{inPlace} file(s) in place, {failed} failed")
    return 1 if failed else 0


def _cmdSubmit(args):
    """Build a job area for the selected samples and submit them. Use --dryRun first for testing."""
    sel = _pick(args)
    if args.filesPerJob is not None and args.filesPerJob < 1:
        sys.exit(f"--filesPerJob must be at least 1, got {args.filesPerJob}")
    if args.maxFiles is not None and args.maxFiles < 1:
        sys.exit(f"--maxFiles must be at least 1, got {args.maxFiles}")
    if args.content:
        for s in sel:
            s["content"] = args.content
    print(f"Task '{args.task}' : {len(sel)} sample(s), backend={args.backend}")

    if args.backend == "crab":
        cfgs, base = crabBackend.prepare(sel, args.task, unitsPerJob=args.filesPerJob, maxFiles=args.maxFiles, maxMemoryMB=args.memoryMB, base=args.outputBase)
        print(f"  Wrote {len(cfgs)} crab config(s) under {taskDir(args.task, create=False)}")
        print(f"  Output goes to {outputDir(base, args.task)}")
        bad = crabBackend.submit(cfgs, dryRun=args.dryRun, taskName=args.task, base=base)[1]
        return 1 if bad else 0

    fileLists = {}
    for s in sel:
        lfns = das.listFiles(s["dataset"], s["dasInstance"], refresh=args.refresh)
        if args.maxFiles:
            lfns = lfns[: args.maxFiles]
        fileLists[s["name"]] = lfns
        print(f"  {s['name']:<48} {len(lfns):>5} file(s)")
    d, nJobs, base = condorBackend.prepare(sel, args.task, fileLists, filesPerJob=args.filesPerJob, maxFiles=args.maxFiles, memoryMB=args.memoryMB, base=args.outputBase)
    print(f"  Wrote {nJobs} job(s) under {d}")
    print(f"  Output goes to {outputDir(base, args.task)}")
    if not nJobs:
        sys.exit("  No jobs to submit; every selected sample came back with no input files")
    return condorBackend.submit(args.task, dryRun=args.dryRun, base=base)


def _cmdSelection(args):
    """Show what a selection applies. Given a name and an --era, prints the selection resolved for that era, as select applies it. With no name, lists the selections of each run and the eras they declare."""
    files = selectionFiles()
    if not args.selection:
        for run in RUNS:
            mine = [(name, selectionEras(name, folder)) for r, folder, name in files if r == run]
            if not mine:
                continue
            width = max(len(name) for name, _ in mine)
            print(run)
            for name, eras in mine:
                print(f"  {name:<{width}}  {', '.join(eras) if eras else f'every {run} era'}")
        return 0
    if not args.era:
        sys.exit(f"Give an --era, since the era picks the run folder and every era-keyed threshold. Known eras: {', '.join(e for run in RUNS for e in _runEras()[run])}")
    _checkEra(args.era)
    try:
        resolved = resolveSelection(args.selection, era=args.era)
    except FileNotFoundError as e:
        sys.exit(f"Error: {e}{_otherRunHint(args.selection, {run: [n for r, _, n in files if r == run] for run in RUNS}, args.era)}")
    if args.write:
        with open(args.write, "w") as f:
            json.dump(resolved, f, indent=2)
        print(f"Wrote {args.write}")
        return 0
    print(json.dumps(resolved, indent=2))
    return 0


def _cmdSelect(args):
    """Apply an event-level selection to ntuples and write ntuples with the same branches."""
    sel = _pick(args)
    if args.maxFiles is not None and args.maxFiles < 1:
        sys.exit(f"--maxFiles must be at least 1, got {args.maxFiles}")
    if args.filesPerJob < 1:
        sys.exit(f"--filesPerJob must be at least 1, got {args.filesPerJob}")
    print(f"Task '{args.task}' : {len(sel)} sample(s), selection={args.selection}, backend={args.backend}")
    plan = selectBackend.preparePass(sel, args.selection, args.task, args.inputTask, backend=args.backend, inputBase=args.inputBase, maxFiles=args.maxFiles)
    if args.backend == "local":
        if args.outputBase:
            print("  --outputBase applies to condor only, so this local pass writes under ntupleSelection/out/")
        return selectBackend.runLocal(plan, dryRun=args.dryRun)
    d, nJobs, outDir = selectBatch.prepare(plan, filesPerJob=args.filesPerJob, base=args.outputBase)
    print(f"  Wrote {nJobs} job(s) under {d}")
    print(f"  Output goes to {outDir}")
    return selectBatch.submit(args.task, dryRun=args.dryRun)


def _cmdNorm(args):
    """Record the generator weight sum every yield is divided by. MC only, since data has no generator weights."""
    sel = _pick(args)
    data = [s["name"] for s in sel if not s.get("isMC")]
    sel = [s for s in sel if s.get("isMC")]
    if data:
        print(f"  Skipping {len(data)} data sample(s); a generator weight sum has no meaning there")
    if not sel:
        sys.exit("No MC samples matched the selection")

    ## DAS has no weight sums, so they are read from the central NanoAOD, which covers the whole dataset.
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
    """Print the cutflow a select task recorded, summing a condor pass's job cutflows."""
    selectBackend.printCutflow(args.task)


def _cmdStatus(args):
    """Show how a submitted task is doing: what it ran, its jobs on the queue, and how many of its outputs are on EOS."""
    d, info = _taskRecord(args.task)

    # Print the few lines that matter; the record embeds every resolved preset and runs to tens of kB.
    prov = info.get("provenance", {})
    print(f"Task     {info.get('task')}  ({info.get('backend')})")
    if info.get("stage") == "select":
        print(f"Samples  {len(info.get('samples', []))}, selection {info.get('selection')} on {info.get('inputTask')}")
    else:
        print(f"Samples  {len(info.get('samples', []))}, content {', '.join(info.get('content') or sorted({c for c in [detail.get('content') for detail in info.get('sampleDetails', [])] if c}))}")
    if info.get("nJobs") is not None:
        print(f"Jobs     {info['nJobs']}")
    if prov:
        dirty = " (dirty tree)" if prov.get("dirty") else ""
        print(f"From     {str(prov.get('commit'))[:8]} on {prov.get('branch')}{dirty}, by {prov.get('submittedBy')} at {prov.get('submittedAt')}")
    print(f"Output   {recordedOutputDir(info)}")
    print(f"Record   {os.path.join(d, 'task.json')}")

    if info.get("stage") == "select":
        return _selectionStatus(args.task, info)
    if info.get("backend") == "crab":
        crabBackend.status(args.task)
        return 0
    return condorBackend.status(args.task)


def _selectionStatus(taskName, info):
    """A condor selection pass's jobs on each schedd it was submitted to, then how many of its selected ntuples are on EOS."""
    pairs = condorBackend.submissions(info)
    if not pairs:
        print("\nNot submitted, since the record holds no condor cluster")
        return 0
    for schedd, cluster in pairs:
        runTool(["condor_q", "-nobatch"] + (["-name", schedd] if schedd else []) + [str(cluster)])
    state = condorBackend.queueState(info)
    unknown = ", ".join(f"{cluster} on {schedd or 'the default schedd'}" for schedd, cluster in state["unknown"])
    print(f"Queue    {state['active']} job(s) idle or running, {state['held']} held" + (f"; condor_q could not answer for cluster {unknown}" if unknown else ""))
    try:
        missing, nPresent, nExpected = selectBatch.missingJobs(taskName)
    except RuntimeError as e:
        print(f"Outputs  unknown, since EOS could not be listed: {e}")
        return 0
    print(f"Outputs  {nPresent}/{nExpected} present on EOS")
    return 0


def _cmdResubmit(args):
    """Resubmit the jobs of a production task whose outputs never reached EOS."""
    d, info = _taskRecord(args.task)

    print(f"Task     {info.get('task')}  ({info.get('backend')})")
    print(f"Output   {recordedOutputDir(info)}")

    if info.get("stage") == "select":
        sys.exit(f"Task '{args.task}' is a selection pass, and resubmit reruns production jobs only. ./kamui status --task {args.task} shows which of its outputs are on EOS.")
    if info.get("backend") == "crab":
        # CRAB knows which of its own jobs failed, and writes their output to the same place.
        n, failed = crabBackend.resubmit(args.task, dryRun=args.dryRun)
        print(f"  {'Would ask' if args.dryRun else 'Asked'} crab to resubmit failed jobs in {n} project(s)")
        if failed:
            sys.exit(f"  Still not submitted: {', '.join(failed)}")
        return 0

    ## A task that never went out has nothing to retry, and a retry would send every job while submit still treats the area as unused and may clear it
    if not condorBackend.submissions(info):
        sys.exit(f"Task '{args.task}' was never submitted, so it has nothing to retry. Run the same ./kamui submit without --dryRun.")
    missing, nPresent, nExpected = condorBackend.missingJobs(args.task)
    print(f"Outputs  {nPresent}/{nExpected} present on EOS")
    if not missing:
        print("  Nothing to resubmit")
        return 0
    print(f"Missing  {len(missing)} job(s):")
    for row in missing[:20]:
        sampleName, index = row.split(",")[0], row.split(",")[1]
        print(f"           {sampleName}  job {index}")
    if len(missing) > 20:
        print(f"           ... and {len(missing) - 20} more")

    n, nJobs, code = condorBackend.resubmit(args.task, dryRun=args.dryRun, rows=missing, force=args.forceResubmit)
    if code != 0:
        sys.exit(f"  condor_submit failed with code {code}")
    if not args.dryRun:
        print(f"  Retry {n} submitted: {nJobs} job(s), logs in logs/retry{n}, output to the same directory")
    return 0


def _cmdCheck(args):
    """Offline validation of every config file."""
    problems = []
    ## One entry per named check; a "warn" is an incomplete check and does not fail the run.
    report = []

    def note(label, state, text):
        report.append((label, state, text))

    cat = loadCatalog()
    bad = len([s for s in cat if not s["dataset"].startswith("/") or s["dataset"].count("/") != 3])
    dupes = len(cat) - len({s["name"] for s in cat})
    for s in cat:
        if not s["dataset"].startswith("/") or s["dataset"].count("/") != 3:
            problems.append(f"Sample '{s['name']}' has a malformed dataset path")
    if dupes:
        problems.append(f"{dupes} duplicate sample name(s)")
    note("Catalog", "pass" if not bad and not dupes else "fail", f"Every sample is listed once and is well-formatted ({len(cat)} samples in {len({s.get('family') for s in cat})} families)")

    sites = loadSites()
    eras = _runEras(cat, sites)

    ## Resolving builds exactly what a job receives, so every preset and collection file is resolved as MC and as data for each era of its run.
    presets, collections = listPresets(), listCollections()
    nOk = nTried = 0
    failures, parked = {}, []
    for run in RUNS:
        for name in presets.get(run, []) + collections.get(run, []):
            if name in PARKED_CONTENT.get(run, ()):
                parked.append(f"{run}/{name}")
                continue
            for era in eras[run]:
                for isMC in (True, False):
                    nTried += 1
                    try:
                        resolveContent(name, isMC=isMC, era=era)
                        nOk += 1
                    except Exception as e:                            # noqa: BLE001
                        failures.setdefault((run, name, str(e)), []).append(f"{era} {'MC' if isMC else 'data'}")
    ## A file broken the same way for every era is reported once
    for (run, name, error), where in failures.items():
        problems.append(f"Content '{run}/{name}' for {', '.join(where)}: {error}")
    unknownPreset = [s for s in cat if s["content"] not in presets.get(eraGroup(s["era"]), [])]
    for s in unknownPreset:
        problems.append(f"Sample '{s['name']}' is {s['era']} ({eraGroup(s['era'])}) but wants content preset '{s['content']}', which that era does not define")
    note("Content", "pass" if nOk == nTried and not unknownPreset else "fail", f"Every preset and collection resolves for each era of its run, as MC and as data ({nOk}/{nTried})")
    if parked:
        note("Parked content", "warn", f"Not checked while its configuration is unfinished: {', '.join(parked)}")

    ## Resolving a selection collapses every era-keyed value and checks every cut type and quantity name. One that names no eras is resolved for each era of its run, as select does.
    nSel = nSelTried = 0
    for run, selDir, name in selectionFiles():
        for era in (selectionEras(name, selDir) or eras[run] or [None]):
            nSelTried += 1
            try:
                resolveSelection(name, selDir, era=era)
                nSel += 1
            except Exception as e:                                    # noqa: BLE001
                problems.append(f"Selection '{run}/{name}' for era '{era}': {e}")
    note("Selections", "pass" if nSel == nSelTried else "fail", f"Every selection resolves for each era ({nSel}/{nSelTried})")

    ## A definition resolves for each era it is keyed by, or for every era of its run when it has none.
    nDef = nDefTried = 0
    for run, defDir, name in definitionFiles():
        for era in (definitionEras(name, defDir) or eras[run]):
            nDefTried += 1
            try:
                resolveRequirements(f"definition '{run}/{name}'", [{"definition": name}], era)
                nDef += 1
            except Exception as e:                                    # noqa: BLE001
                problems.append(f"Definition '{run}/{name}' for era '{era}': {e}")
    note("Definitions", "pass" if nDef == nDefTried else "fail", f"Every definition resolves for each era ({nDef}/{nDefTried})")

    ## A trigger file keyed by era is resolved for each era it lists, and each of those must be an era of the file's run
    nTrig = len(listTriggerConfigs())
    trigProblems = validateTriggers(eras)
    problems += trigProblems
    note("Triggers", "pass" if not trigProblems else "fail", f"Every trigger file is well-formatted ({nTrig - len(trigProblems)}/{nTrig})")

    normProblems = validateNormalizations()
    problems += normProblems
    note("Normalizations", "pass" if not normProblems else "fail", "Every file in config/normalizations/ is well-formatted")

    ## Generator sums are measured data that grow with the catalog, so a missing one is reported and never fails the run
    mc = [s["name"] for s in cat if s["isMC"]]
    noCount, noSumw = normalization.missingSums(mc)
    missing = sorted(set(noCount) | set(noSumw))
    note("Generator sums", "warn" if missing else "pass", f"MC samples that know their total generator weight ({len(mc) - len(missing)}/{len(mc)})" + (f"; run './kamui norm --write' for the rest, for example {missing[0]}" if missing else ""))

    missingKeys = [k for k in ("eosRedirector", "sourceRedirector", "stageoutBase", "miniaodDir", "crabStageoutBase", "crabStorageSite") if k not in sites]
    badTags = [era for era, v in (sites.get("globalTags") or {}).items() if not isinstance(v, dict) or not all(isinstance(v.get(f), str) and v.get(f) for f in ("mc", "data"))]
    missingCfg = [f for f in ("ntuple_cfg.py", "ntupleTables.py") if not os.path.exists(os.path.join(paths.CMSSW_DIR, f))]
    for k in missingKeys:
        problems.append(f"sites.json is missing '{k}'")
    for f in missingCfg:
        problems.append(f"Missing cmssw/{f}")
    for era in badTags:
        problems.append(f"sites.json globalTags['{era}'] needs an 'mc' and a 'data' tag")
    note("Sites and CMSSW", "pass" if not missingKeys and not missingCfg and not badTags else "fail", "Validated sites.json and the CMSSW job script configurations")

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
        print(f"  Age      {st['newestDays']:.1f} to {st['oldestDays']:.1f} days")
        print(f"  Expired  {st['nStale']} (older than {das.CACHE_MAX_AGE_DAYS} days, ignored on read)")


# Parser!

## The usage line repeats what the help below it already shows, so it is dropped everywhere.
class _Formatter(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        return

    ## argparse measures command names at the parent indent but prints them one level deeper, so the column is widened to the longest name.
    def add_argument(self, action):
        super().add_argument(action)
        if action.nargs == argparse.PARSER:
            widest = max((len(c) for c in action.choices), default=0)
            self._action_max_length = max(self._action_max_length, widest + self._current_indent + 2)

    def _format_action(self, action):
        text = super()._format_action(action)
        ## The subparsers action prints its metavar on a line of its own above the command list.
        if action.nargs == argparse.PARSER:
            text = "\n".join(text.split("\n")[1:])
        return text


## A bad or missing flag gets the plain argparse message and a pointer to the help.
class _CommandParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, f"{self.prog}: error: {message}\nRun ./{self.prog} --help to see its {'flags' if ' ' in self.prog else 'commands'}.\n")


REQUIRED_TITLE = "Required arguments"


def _titles(q):
    q._positionals.title = "Positional arguments"
    q._optionals.title = "Optional arguments"
    return q


## -h is hidden from the help because a reader who got here already found it. Required flags get their own group, listed before the optional ones.
def _addCmd(sub, name, help, description):
    q = sub.add_parser(name, help=help, description=description, formatter_class=_Formatter, add_help=False)
    q.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    q.add_argument_group(REQUIRED_TITLE)
    q._action_groups.insert(1, q._action_groups.pop())
    return _titles(q)


def _required(q):
    """The group a command's required flags go in."""
    return next(g for g in q._action_groups if g.title == REQUIRED_TITLE)


## Commands are added in the order python/kamui/README.md describes them, which is the order --help lists them.
def main(argv=None):
    p = _CommandParser(prog="kamui", description=__doc__, formatter_class=_Formatter, add_help=False)
    p.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    _titles(p)._positionals.title = "Commands"
    sub = p.add_subparsers(dest="cmd", metavar="command", prog="kamui", parser_class=_CommandParser)

    q = _addCmd(sub, "check", help="Validate configuration files", description=_cmdCheck.__doc__)
    q.set_defaults(func=_cmdCheck)

    q = _addCmd(sub, "find", help="Unrestricted DAS dataset search", description=_cmdFind.__doc__)
    q.add_argument("pattern", help="DAS wildcard, e.g. '/*HAHM*/*/MINIAODSIM'")
    q.add_argument("--instance", metavar="INSTANCE", default="prod/global", help="prod/global for official datasets, prod/phys03 for USER ones (default: %(default)s)")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdFind)

    q = _addCmd(sub, "norm", help="Measure and store weights for normalization", description=_cmdNorm.__doc__)
    _addSelection(q)
    q.add_argument("--write", action="store_true", help="Store the sums in config/normalizations/generatorSums.json")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdNorm)

    q = _addCmd(sub, "list", help="Show all available samples", description=_cmdList.__doc__)
    _addSelection(q)
    q.add_argument("--datasets", action="store_true", help="Print DAS paths only")
    q.set_defaults(func=_cmdList)

    q = _addCmd(sub, "query", help="Query DAS for how many files, events and GB each selected sample holds", description=_cmdQuery.__doc__)
    _addSelection(q)
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdQuery)

    q = _addCmd(sub, "stage", help="Copy a sample's MiniAOD files to EOS", description=_cmdStage.__doc__)
    _addSelection(q)
    q.add_argument("--maxFiles", metavar="N", type=int, help="Hard cap on files copied")
    q.add_argument("--dryRun", action="store_true", help="Print what would be copied, but copy nothing")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.set_defaults(func=_cmdStage)

    q = _addCmd(sub, "content", help="Show presets declaring what we save in ntuples", description=_cmdContent.__doc__)
    q.add_argument("preset", nargs="?", help="Preset or collection file name; omit it to list the presets")
    q.add_argument("--data", action="store_true", help="Resolve as data (drops mcOnly collections)")
    q.add_argument("--era", metavar="NAME", default="Summer24", help="Era configuration we use (default: %(default)s)")
    q.add_argument("--write", metavar="PATH", help="Write the resolved JSON here")
    q.set_defaults(func=_cmdContent)

    q = _addCmd(sub, "submit", help="Produce ntuples by submitting to condor or CRAB", description=_cmdSubmit.__doc__)
    _addSelection(q)
    _required(q).add_argument("--task", metavar="NAME", required=True, help="Task name; also the EOS output subdirectory")
    q.add_argument("--backend", metavar="BACKEND", choices=["condor", "crab"], default="condor", help="Where the jobs run (default: %(default)s)")
    q.add_argument("--content", metavar="NAME", help="Override the per-sample content preset")
    q.add_argument("--filesPerJob", metavar="N", type=int, help=f"Input files per job, overriding any per-sample unitsPerJob (default: the sample's unitsPerJob, else {condorBackend.DEFAULT_FILES_PER_JOB})")
    q.add_argument("--maxFiles", metavar="N", type=int, help="Use at most this many input files per sample")
    q.add_argument("--memoryMB", metavar="N", type=int, default=2500, help="Memory request per job in MB (default: %(default)s)")
    q.add_argument("--dryRun", action="store_true", help="Write the job area, submit nothing")
    q.add_argument("--refresh", action="store_true", help="Bypass the DAS cache")
    q.add_argument("--outputBase", metavar="PATH", help="Write output under this EOS path (default: the backend's base in sites.json)")
    q.set_defaults(func=_cmdSubmit)

    q = _addCmd(sub, "status", help="Status of a submitted task", description=_cmdStatus.__doc__)
    _required(q).add_argument("--task", metavar="NAME", required=True, help="A task under ntupleProduction/jobs/ or ntupleSelection/jobs/")
    q.set_defaults(func=_cmdStatus)

    q = _addCmd(sub, "resubmit", help="Rerun failed jobs", description=_cmdResubmit.__doc__)
    _required(q).add_argument("--task", metavar="NAME", required=True, help="The production task to retry")
    q.add_argument("--dryRun", action="store_true", help="Report what would be resubmitted, submit nothing")
    q.add_argument("--forceResubmit", action="store_true", help="Resubmit even while jobs from this task may still be on the queue, held, or on a schedd condor_q cannot reach")
    q.set_defaults(func=_cmdResubmit)

    q = _addCmd(sub, "selection", help="List the selections, or show one resolved for an era", description=_cmdSelection.__doc__)
    q.add_argument("selection", nargs="?", help="Selection name, or names joined by commas; omit it to list the selections")
    q.add_argument("--era", metavar="NAME", help="The era to resolve for, which picks the run folder and every era-keyed threshold")
    q.add_argument("--write", metavar="PATH", help="Write the resolved JSON here instead of printing it")
    q.set_defaults(func=_cmdSelection)

    q = _addCmd(sub, "select", help="Apply an event selection to ntuples", description=_cmdSelect.__doc__)
    _addSelection(q)
    _required(q).add_argument("--selection", metavar="NAME", required=True, help="Selection config name, e.g. lepton, read from the run folder of the samples' era. Names joined by commas run one after another, e.g. lepton,dv3x4")
    _required(q).add_argument("--task", metavar="NAME", required=True, help="Name for this selection pass")
    _required(q).add_argument("--inputTask", metavar="NAME", required=True, help="The ntuple production task to read from")
    q.add_argument("--inputBase", metavar="PATH", help="Base holding <base>/ntuples/<inputTask>, on EOS or a local directory (default: the output directory the input task's task.json records, else the site stageout base)")
    q.add_argument("--outputBase", metavar="PATH", help="EOS base for the selected ntuples, condor only (default: the site stageout base)")
    q.add_argument("--backend", metavar="BACKEND", choices=["local", "condor"], default="local", help="Where the selection runs (default: %(default)s)")
    q.add_argument("--filesPerJob", metavar="N", type=int, default=selectBatch.DEFAULT_FILES_PER_JOB, help="Input files per job on condor (default: %(default)s)")
    q.add_argument("--maxFiles", metavar="N", type=int, help="Use at most this many input files per sample")
    q.add_argument("--dryRun", action="store_true", help="Locally, print what the pass would read, write and apply. On condor, write the job area and submit nothing")
    q.set_defaults(func=_cmdSelect)

    q = _addCmd(sub, "cutflow", help="Print the cutflow for a given task", description=_cmdCutflow.__doc__)
    _required(q).add_argument("--task", metavar="NAME", required=True, help="A select task, local or condor")
    q.set_defaults(func=_cmdCutflow)

    q = _addCmd(sub, "cache", help="Inspect or clear the DAS cache", description=_cmdCache.__doc__)
    q.add_argument("--clear", action="store_true", help="Delete every cached response")
    q.add_argument("--prune", action="store_true", help="Delete only the expired entries, keeping the rest")
    q.set_defaults(func=_cmdCache)

    ## Commands print between the outputs of condor_q, crab and xrdcp, so each line goes out at once to keep that order when the output is piped or logged
    sys.stdout.reconfigure(line_buffering=True)
    ## The banner is an orientation aid, so it appears with the help and stays out of the way otherwise.
    given = list(argv if argv is not None else sys.argv[1:])
    printBanner(enabled=not given or "-h" in given or "--help" in given)
    args, unknown = p.parse_known_args(argv)
    ## A flag the command does not take is reported by that command, so the pointer leads to its own help
    if unknown:
        (sub.choices[args.cmd] if args.cmd else p).error(f"unrecognized arguments: {' '.join(unknown)}")
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
    except (FileNotFoundError, PermissionError, ValueError, RuntimeError, das.DasError) as e:
        # Config, storage and DAS problems are user errors: say what is wrong and stop. Anything else raises.
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    sys.exit(main())
