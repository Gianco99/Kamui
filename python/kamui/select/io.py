"""
Planning a selection pass, running it locally, and recording what it did for the ntupleSelection stage.

A pass reads the ntuples of one production task, named by --inputTask, and writes its outputs under its own task name. Locally that is ntupleSelection/out/<task>/, and on condor <base>/selected/<task>/ on EOS, with the job area in ntupleSelection/jobs/<task>/.
"""

# Import Block

## Standard Python imports
import json
import os
import shutil
import subprocess
import tempfile

## Kamui modules
from ..foundations import paths
from ..configReaders.selections import resolveSelection
from ..configReaders.sites import loadSites
from ..submit.common import checkTaskName, eosListing, readTaskRecord, recordedOutputDir, writeTaskRecord
from .engine import MissingCollections, applySelection, collectionsUsed, mergeNotes
from .normalization import generatedEvents

## What each condor selection job leaves on EOS, in <outputDir>/<sample>/
SELECTED_NAME = "{sample}_selected_{index}.root"
CUTFLOW_NAME = "{sample}_cutflow_{index}.json"


# Matching whole path components keeps '..._2016' from claiming the files of '..._2016APV'
def _namesSample(path, sampleName):
    """Whether a path has the sample as one of its directory components."""
    return sampleName in path.replace(os.sep, "/").split("/")


def productionRecord(inputTask):
    """The task.json in a production task's job area, or None when there is none."""
    d = os.path.join(paths.JOBS_DIR, checkTaskName(inputTask))
    return readTaskRecord(d) if os.path.isfile(os.path.join(d, "task.json")) else None


def inputDir(inputTask, inputBase=None, sites=None):
    """Where a production task's ntuples are: <inputBase>/ntuples/<inputTask> when a base is given, else the directory its task.json records, else the one under stageoutBase."""
    checkTaskName(inputTask)
    if inputBase:
        return "/".join([inputBase.rstrip("/"), "ntuples", inputTask])
    recorded = recordedOutputDir(productionRecord(inputTask) or {})
    if recorded:
        return recorded.rstrip("/")
    return "/".join([(sites or loadSites())["stageoutBase"].rstrip("/"), "ntuples", inputTask])


# Condor writes <task>/<sample>/*.root and CRAB nests under <task>/<primaryDataset>/<sample>/<timestamp>/0000/, so the whole task is searched for paths naming the sample.
def _rootFiles(directory, local, sites):
    """Every ROOT file under a directory, local or on EOS, as (directory below the searched one, full path)."""
    if local:
        return sorted((os.path.relpath(dirpath, directory), os.path.join(dirpath, f)) for dirpath, _, files in os.walk(directory) for f in files if f.endswith(".root"))
    redirector = sites["eosRedirector"].rstrip("/")
    try:
        r = subprocess.run(["xrdfs", redirector, "ls", "-R", directory], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"Could not list {directory}: {e}")
    if r.returncode != 0:
        ## Only a missing task directory means no ntuples, so a failure such as an expired proxy never passes for an empty production
        if "no such file or directory" in r.stderr.lower():
            return []
        raise RuntimeError(f"Could not list {directory}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
    lines = [line.strip() for line in r.stdout.splitlines() if line.strip().endswith(".root")]
    return sorted((os.path.relpath(os.path.dirname(line), directory), f"{redirector}/{line}") for line in lines)


def _isLocal(directory, inputBase):
    return os.path.isdir(directory) or bool(inputBase and os.path.isdir(inputBase))


def findInputs(inputTask, sampleName, inputBase=None):
    """Every ntuple a production task wrote for one sample. Reads EOS over xrootd, or a local directory."""
    sites = loadSites()
    directory = inputDir(inputTask, inputBase, sites)
    return [p for rel, p in _rootFiles(directory, _isLocal(directory, inputBase), sites) if _namesSample(rel, sampleName)]


def _publishedRecord(directory, local, sites):
    """The task.json published next to a production task's ntuples, or None when it cannot be read."""
    try:
        if local:
            with open(os.path.join(directory, "task.json")) as f:
                return json.load(f)
        r = subprocess.run(["xrdfs", sites["eosRedirector"].rstrip("/"), "cat", directory + "/task.json"], capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


# A task name stands for one pass, so a second pass under it would mix its outputs and cutflow with the first one's.
def checkFreshTask(taskName, backend):
    """Refuse a task name an earlier selection pass used. A condor job area that was never submitted, such as one a dry run left, may be rebuilt."""
    checkTaskName(taskName)
    outDir = os.path.join(paths.SELECTION_OUT_DIR, taskName)
    jobArea = os.path.join(paths.SELECTION_JOBS_DIR, taskName)
    for d in (outDir, jobArea):
        if os.path.islink(d):
            raise ValueError(f"{d} is a symlink, so writing there would leave ntupleSelection/. Remove it first.")
    if os.path.isdir(outDir) and os.listdir(outDir):
        raise ValueError(f"Task '{taskName}' already has the outputs of a local pass in {outDir}. Use a different --task, or remove that directory first.")
    if not (os.path.isdir(jobArea) and os.listdir(jobArea)):
        return
    if backend != "condor":
        raise ValueError(f"Task '{taskName}' already has a condor job area at {jobArea}. Use a different --task, or remove that directory first.")
    try:
        cluster = readTaskRecord(jobArea).get("condorCluster")
    except FileNotFoundError:
        return
    except (OSError, ValueError) as e:
        raise ValueError(f"Could not read {os.path.join(jobArea, 'task.json')} ({e}), so kamui cannot tell whether task '{taskName}' was submitted. Use a different --task.")
    if cluster:
        raise ValueError(f"Task '{taskName}' was submitted to condor cluster {cluster}, so its jobs may still be running. Use a different --task.")


def _missingMessage(selectionName, missing):
    """The error for input ntuples lacking collections a selection reads. `missing` maps each sample to (its content preset or None, the collections it lacks)."""
    lines = [f"Selection '{selectionName}' reads collections these input ntuples do not have:"]
    for name, (preset, lacking) in sorted(missing.items()):
        lines.append(f"  {name}{f' (content preset {preset})' if preset else ''}: {', '.join(lacking)}")
    lines.append("Use an --inputTask whose content preset writes them.")
    return "\n".join(lines)


def _writtenCollections(record, sampleName):
    """The collections a production record says it wrote for one sample, with the sample's preset, or (None, None) when the record does not say."""
    detail = next((d for d in (record or {}).get("sampleDetails", []) if d.get("name") == sampleName), None)
    if not detail:
        return None, None
    ## One preset resolves per era, and the content files of one run hold the same collections, so their union is what the sample has
    written = [c for c in (record.get("resolvedContent") or {}).values() if c.get("name") == detail.get("content") and bool(c.get("isMC")) == bool(detail.get("isMC"))]
    if not written:
        return detail.get("content"), None
    return detail.get("content"), set().union(*(c.get("collections", {}) for c in written))


def preparePass(samples, selectionName, taskName, inputTask, backend="local", inputBase=None, maxFiles=None, sites=None):
    """
    Everything a selection pass needs before it runs on either backend, returned as a dict: each sample's input files and content preset, and the selection resolved for each era.

    Refuses a task name already used, a blind selection on data, and inputs whose recorded content lacks a collection the selection reads.
    """
    sites = sites or loadSites()
    checkFreshTask(taskName, backend)
    directory = inputDir(inputTask, inputBase, sites)
    local = _isLocal(directory, inputBase)
    ## A condor worker cannot see this machine's disks, so it reads every input over xrootd
    if local and backend == "condor":
        raise ValueError(f"{directory} is a local directory, and condor jobs can only read inputs on EOS. Give --inputBase an EOS path such as /store/user/<you>, or run with --backend local.")
    found = _rootFiles(directory, local, sites)

    fileLists, capped = {}, set()
    for s in samples:
        inputs = [p for rel, p in found if _namesSample(rel, s["name"])]
        if not inputs:
            print(f"  {s['name']:<44} No input ntuples under {directory}, skipping")
            continue
        fileLists[s["name"]] = inputs[:maxFiles] if maxFiles else inputs
        if len(fileLists[s["name"]]) < len(inputs):
            capped.add(s["name"])
    if not fileLists:
        raise FileNotFoundError(f"No input ntuples for any selected sample under {directory}")
    chosen = [s for s in samples if s["name"] in fileLists]

    ## One resolved selection per era, since thresholds differ by era
    resolved = {e: resolveSelection(selectionName, era=e) for e in sorted({s["era"] for s in chosen})}
    data = [s["name"] for s in chosen if not s.get("isMC")]
    if data and any(r["blind"] for r in resolved.values()):
        raise ValueError(f"Selection '{selectionName}' is blind, so it never runs on data. Leave out the data sample(s): {', '.join(data)}")

    ## A condor pass on ntuples lacking a collection would fail on every worker, so the input task's record is compared first. Without a record the engine checks each sample's first file instead.
    record = productionRecord(inputTask) or _publishedRecord(directory, local, sites)
    presets, missing = {}, {}
    for s in chosen:
        presets[s["name"]], written = _writtenCollections(record, s["name"])
        lacking = [c for c in collectionsUsed(resolved[s["era"]]) if written is not None and c not in written]
        if lacking:
            missing[s["name"]] = (presets[s["name"]], lacking)
    if missing:
        raise ValueError(_missingMessage(selectionName, missing))

    ## A production or pass capped with --maxFiles reads only part of a dataset, so the cutflow leaves out its whole-dataset generated row
    partial = sorted(s["name"] for s in chosen if (record or {}).get("maxFiles") or s["name"] in capped)
    return {"task": taskName, "backend": backend, "selection": selectionName, "inputTask": inputTask, "inputDir": directory, "maxFiles": maxFiles, "samples": chosen, "fileLists": fileLists, "presets": presets, "resolvedSelections": resolved, "partialInputs": partial}


def writePassRecord(d, plan, outputDir, fields=None, sites=None):
    """Write a selection pass's task.json into d: what it read, the selection it applied for each era, where it wrote, and the code that ran it."""
    record = {"task": plan["task"], "stage": "select", "backend": plan["backend"], "selection": plan["selection"], "inputTask": plan["inputTask"], "inputDir": plan["inputDir"], "maxFiles": plan["maxFiles"], "samples": [s["name"] for s in plan["samples"]], "nInputFiles": {s["name"]: len(plan["fileLists"][s["name"]]) for s in plan["samples"]}, "partialInputs": plan["partialInputs"], "outputDir": outputDir}
    record.update(fields or {})
    record["resolvedSelections"] = plan["resolvedSelections"]
    writeTaskRecord(d, record, samples=plan["samples"], sites=sites)


def _selectedPath(outDir, sampleName):
    return os.path.join(outDir, sampleName, f"{sampleName}_selected.root")


def runLocal(plan, dryRun=False):
    """
    Run a planned pass in this process, writing <sample>/<sample>_selected.root, cutflow.json and task.json under ntupleSelection/out/<task>/.

    The cutflow is rewritten after every sample, so a failure keeps the counts of the samples already done. A dry run prints what the pass would read, write and apply, and touches nothing.
    """
    outDir = os.path.join(paths.SELECTION_OUT_DIR, plan["task"])
    if dryRun:
        for s in plan["samples"]:
            print(f"  {s['name']:<44} {len(plan['fileLists'][s['name']]):>5} input file(s) -> {_selectedPath(outDir, s['name'])}")
        for era, resolved in sorted(plan["resolvedSelections"].items()):
            print(f"\n  Selection '{plan['selection']}' resolved for era {era}:")
            print(json.dumps(resolved, indent=2))
        print("\n  [dryRun] Nothing was read or written")
        return 0

    os.makedirs(outDir, exist_ok=True)
    writePassRecord(outDir, plan, outDir)
    flows = {}
    try:
        for s in plan["samples"]:
            try:
                flow = applySelection(plan["fileLists"][s["name"]], plan["resolvedSelections"][s["era"]], _selectedPath(outDir, s["name"]))
            except MissingCollections as e:
                raise ValueError(_missingMessage(plan["selection"], {s["name"]: (plan["presets"].get(s["name"]), e.collections)}))
            except ValueError as e:
                raise ValueError(f"Sample '{s['name']}': {e}")
            flows[s["name"]] = withGenerated(flow, None if s["name"] in plan["partialInputs"] else generatedEvents(s["name"]))
            writeCutflow(plan["task"], plan["selection"], flows, inputTask=plan["inputTask"])
            print(f"  {s['name']:<44} {flow[0]['kept']:>8,} -> {flow[-1]['kept']:>8,}  ({100 * flow[-1]['kept'] / flow[0]['kept'] if flow[0]['kept'] else 0:.1f}%)")
    except BaseException:
        ## The directory was empty when the pass began, so a pass that finished no sample leaves nothing behind and its task name stays free
        if not flows:
            shutil.rmtree(outDir, ignore_errors=True)
        raise
    print(f"  Selected ntuples, cutflow and task record written under {outDir}")
    return 0


def _saveJson(path, data):
    """Write JSON through a temporary file, so a failure partway cannot leave a broken file."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def writeCutflow(task, selectionName, flows, inputTask=None):
    """Record the per-cut counts for every sample in a local pass."""
    out = os.path.join(paths.SELECTION_OUT_DIR, task)
    os.makedirs(out, exist_ok=True)
    _saveJson(os.path.join(out, "cutflow.json"), {"task": task, "selection": selectionName, "inputTask": inputTask, "samples": flows})


def withGenerated(flow, genEvents):
    """Prepend the generated-event row and rebase every efficiency on it, so the first efficiency in the table is the skim efficiency."""
    if not genEvents:
        return flow
    out = [{"cut": "generated", "type": "", "doc": "Generated events in the whole dataset",
            "detail": "recorded by kamui norm",
            "kept": int(genEvents), "removed": 0, "efficiency": 1.0, "cumulative": 1.0}]
    prev = int(genEvents)
    for row in flow:
        r = dict(row)
        r["removed"] = max(prev - r["kept"], 0)
        r["efficiency"] = (r["kept"] / prev) if prev else 0.0
        r["cumulative"] = (r["kept"] / int(genEvents)) if genEvents else 0.0
        out.append(r)
        prev = r["kept"]
    return out


def sumFlows(flows):
    """One cutflow from the cutflows of jobs that read different files of a sample. Every job ran the same cuts, so the rows add up by position."""
    names = [r["cut"] for r in flows[0]]
    if any([r["cut"] for r in f] != names for f in flows):
        raise ValueError("The jobs' cutflows list different cuts, so they cannot be summed")
    total = sum(f[0]["kept"] for f in flows)
    out, prev = [], None
    for i, first in enumerate(flows[0]):
        kept = sum(f[i]["kept"] for f in flows)
        row = dict(first, kept=kept, detail=mergeNotes([f[i].get("detail", "") for f in flows]))
        if prev is None:
            row.update(removed=0, efficiency=1.0, cumulative=1.0)
        else:
            row.update(removed=prev - kept, efficiency=(kept / prev) if prev else 0.0, cumulative=(kept / total) if total else 0.0)
        out.append(row)
        prev = kept
    return out


def loadCutflow(task, sites=None):
    """The cutflow record of a select task: the one a local pass wrote, or the sum of a condor pass's per-job cutflows."""
    checkTaskName(task)
    jobArea = os.path.join(paths.SELECTION_JOBS_DIR, task)
    if os.path.isfile(os.path.join(jobArea, "task.json")):
        return _condorCutflow(task, jobArea, sites or loadSites())
    path = os.path.join(paths.SELECTION_OUT_DIR, task, "cutflow.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No cutflow for task '{task}': there is no {path}, and no condor job area at {jobArea}")
    with open(path) as f:
        return json.load(f)


# Each condor job leaves its own cutflow on EOS beside its ntuple. Their sum is kept in the job area, and read again from EOS until every job has reported.
def _condorCutflow(task, jobArea, sites):
    cache = os.path.join(jobArea, "cutflow.json")
    if os.path.isfile(cache):
        with open(cache) as f:
            cached = json.load(f)
        if cached.get("jobsReported") == cached.get("nJobs"):
            return cached
    record = readTaskRecord(jobArea)
    if not record.get("condorCluster"):
        raise ValueError(f"Task '{task}' was never submitted, so it has no cutflow yet")
    outDir = recordedOutputDir(record)
    redirector = sites["eosRedirector"].rstrip("/")
    with open(os.path.join(jobArea, "jobList.txt")) as f:
        rows = [line.strip().split(",") for line in f if line.strip()]

    listings, found = {}, []
    for sampleName, index, _ in rows:
        if sampleName not in listings:
            listings[sampleName] = eosListing(redirector, f"{outDir}/{sampleName}")
        name = CUTFLOW_NAME.format(sample=sampleName, index=index)
        if name in listings[sampleName]:
            found.append((sampleName, name))

    perSample = {}
    scratch = tempfile.mkdtemp(prefix="kamuiCutflow")
    try:
        if found:
            r = subprocess.run(["xrdcp", "-f", "-s", "--parallel", "4"] + [f"{redirector}/{outDir}/{s}/{n}" for s, n in found] + [scratch + "/"], capture_output=True, text=True, timeout=1800)
            if r.returncode != 0:
                raise RuntimeError(f"Could not copy the job cutflows from {outDir}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
        for sampleName, name in found:
            with open(os.path.join(scratch, name)) as f:
                perSample.setdefault(sampleName, []).append(json.load(f))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    summed = {"task": task, "selection": record.get("selection"), "inputTask": record.get("inputTask"), "nJobs": len(rows), "jobsReported": len(found), "samples": {s: withGenerated(sumFlows(flows), None if s in record.get("partialInputs", []) else generatedEvents(s)) for s, flows in sorted(perSample.items())}}
    _saveJson(cache, summed)
    return summed


def printCutflow(task):
    """Print the cutflow table for a select task."""
    record = loadCutflow(task)

    print(f"Task {record['task']}  selection {record['selection']}\n")
    if record.get("jobsReported") != record.get("nJobs"):
        print(f"Only {record['jobsReported']} of {record['nJobs']} condor jobs have left a cutflow on EOS, so these counts cover only those jobs.\n")
    for sample, flow in sorted(record["samples"].items()):
        print(sample)
        print(f"  {'Cut':<16} {'Type':<9} {'Events':>11} {'Removed':>10} {'Step Eff':>10} {'Cumulative':>12}")
        for row in flow:
            print(f"  {row['cut']:<16} {row.get('type',''):<9} {row['kept']:>11,} {row.get('removed',0):>10,} {100 * row['efficiency']:>9.2f}% {100 * row['cumulative']:>11.2f}%")
            ## What the cut actually is, so the table explains itself without opening the config
            if row.get("doc"):
                print(f"      {row['doc']}")
            if row.get("detail"):
                print(f"      Applied as: {row['detail']}")
        print()

    ## Summed only when every sample ran the same cuts: a sample with no recorded generator count has no `generated` row, and summing by position would add different cuts together
    if len(record["samples"]) > 1:
        flows = list(record["samples"].values())
        names = [r["cut"] for r in flows[0]]
        if any([r["cut"] for r in f] != names for f in flows):
            print("All samples: not totaled, the samples did not all run the same cuts")
            return
        print("All samples")
        print(f"  {'Cut':<16} {'Events':>12} {'Cumulative':>12}")
        first = None
        for i, cut in enumerate(names):
            total = sum(f[i]["kept"] for f in flows)
            first = total if first is None else first
            print(f"  {cut:<16} {total:>12,} {100 * total / first if first else 0:>11.2f}%")
