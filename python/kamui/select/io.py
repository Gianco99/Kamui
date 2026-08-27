"""
Finding input ntuples and recording the cutflow for the ntupleSelection stage.
"""

# Import Block

## Standard Python imports
import json
import os
import subprocess

## Kamui modules
from ..configReaders.sites import loadSites


def findInputs(inputTask, sampleName, inputBase=None):
    """Every ntuple a production task wrote for one sample. Reads EOS over xrootd, or a local directory."""
    sites = loadSites()
    base = (inputBase or sites["stageoutBase"]).rstrip("/")

    ## Condor writes <task>/<sample>/*.root while CRAB nests under <task>/<primaryDataset>/<sample>/<timestamp>/0000/.
    ## Searching the whole task and keeping paths that name the sample handles both.
    if os.path.isdir(base):
        root = os.path.join(base, "ntuples", inputTask)
        if not os.path.isdir(root):
            return []
        return sorted(os.path.join(dirpath, f)
                      for dirpath, _, files in os.walk(root)
                      for f in files
                      if f.endswith(".root") and sampleName in os.path.join(dirpath, f))

    redirector = sites["eosRedirector"].rstrip("/")
    remote = "/".join([base, "ntuples", inputTask])
    try:
        r = subprocess.run(["xrdfs", redirector, "ls", "-R", remote], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    return sorted(f"{redirector}/{line.strip()}" for line in r.stdout.splitlines()
                  if line.strip().endswith(".root") and sampleName in line)


def writeCutflow(selectionDir, task, selectionName, flows):
    """Record the per-cut counts for every sample in a task."""
    out = os.path.join(selectionDir, "out", task)
    os.makedirs(out, exist_ok=True)
    record = {"task": task, "selection": selectionName, "samples": flows}
    tmp = os.path.join(out, "cutflow.json.tmp")
    with open(tmp, "w") as f:
        json.dump(record, f, indent=2)
    os.replace(tmp, os.path.join(out, "cutflow.json"))


def printCutflow(selectionDir, task):
    """Print the cutflow table for a select task."""
    path = os.path.join(selectionDir, "out", task, "cutflow.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"no cutflow at {path}")
    with open(path) as f:
        record = json.load(f)

    print(f"task {record['task']}  selection {record['selection']}\n")
    for sample, flow in sorted(record["samples"].items()):
        print(sample)
        print(f"  {'cut':<16} {'type':<9} {'events':>11} {'removed':>10} {'step eff':>10} {'cumulative':>12}")
        for row in flow:
            print(f"  {row['cut']:<16} {row.get('type',''):<9} {row['kept']:>11,} {row.get('removed',0):>10,} "
                  f"{100 * row['efficiency']:>9.2f}% {100 * row['cumulative']:>11.2f}%")
            ## What the cut actually is, so the table explains itself without opening the config
            if row.get("doc"):
                print(f"      {row['doc']}")
            if row.get("detail"):
                print(f"      applied as: {row['detail']}")
        print()

    ## Totals across samples, since a task usually spans several
    if len(record["samples"]) > 1:
        names = [r["cut"] for r in next(iter(record["samples"].values()))]
        print("all samples")
        print(f"  {'cut':<16} {'events':>12} {'cumulative':>12}")
        first = None
        for i, cut in enumerate(names):
            total = sum(flow[i]["kept"] for flow in record["samples"].values() if i < len(flow))
            first = total if first is None else first
            print(f"  {cut:<16} {total:>12,} {100 * total / first if first else 0:>11.2f}%")
