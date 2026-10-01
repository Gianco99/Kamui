"""
Finding input ntuples and recording the cutflow for the ntupleSelection stage.
"""

# Import Block

## Standard Python imports
import json
import os
import subprocess

## Kamui modules
from ..foundations import paths
from ..configReaders.sites import loadSites


# Matching whole path components keeps '..._2016' from claiming the files of '..._2016APV'
def _namesSample(path, sampleName):
    """Whether a path has the sample as one of its directory components."""
    return sampleName in path.replace(os.sep, "/").split("/")


def findInputs(inputTask, sampleName, inputBase=None):
    """Every ntuple a production task wrote for one sample. Reads EOS over xrootd, or a local directory."""
    sites = loadSites()
    base = (inputBase or sites["stageoutBase"]).rstrip("/")

    ## Condor writes <task>/<sample>/*.root and CRAB nests under <task>/<primaryDataset>/<sample>/<timestamp>/0000/, so the whole task is searched for paths naming the sample
    if os.path.isdir(base):
        root = os.path.join(base, "ntuples", inputTask)
        if not os.path.isdir(root):
            return []
        return sorted(os.path.join(dirpath, f)
                      for dirpath, _, files in os.walk(root)
                      for f in files
                      if f.endswith(".root") and _namesSample(dirpath, sampleName))

    redirector = sites["eosRedirector"].rstrip("/")
    remote = "/".join([base, "ntuples", inputTask])
    try:
        r = subprocess.run(["xrdfs", redirector, "ls", "-R", remote], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"Could not list {remote}: {e}")
    if r.returncode != 0:
        ## Only a missing task directory means no ntuples, so a failure such as an expired proxy never passes for an empty production
        if "no such file or directory" in r.stderr.lower():
            return []
        raise RuntimeError(f"Could not list {remote}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
    return sorted(f"{redirector}/{line.strip()}" for line in r.stdout.splitlines()
                  if line.strip().endswith(".root") and _namesSample(os.path.dirname(line.strip()), sampleName))


def writeCutflow(task, selectionName, flows):
    """Record the per-cut counts for every sample in a task."""
    out = os.path.join(paths.SELECTION_OUT_DIR, task)
    os.makedirs(out, exist_ok=True)
    record = {"task": task, "selection": selectionName, "samples": flows}
    tmp = os.path.join(out, "cutflow.json.tmp")
    with open(tmp, "w") as f:
        json.dump(record, f, indent=2)
    os.replace(tmp, os.path.join(out, "cutflow.json"))


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


def printCutflow(task):
    """Print the cutflow table for a select task."""
    path = os.path.join(paths.SELECTION_OUT_DIR, task, "cutflow.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No cutflow at {path}")
    with open(path) as f:
        record = json.load(f)

    print(f"Task {record['task']}  selection {record['selection']}\n")
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
