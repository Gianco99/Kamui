"""
The generator sums a sample must be normalized by.

These belong to the whole dataset as it was generated, not to whatever subset a job
happened to read, so they are never measured from our own output. They are read from
the sample's central NanoAOD and stored. A skim or a capped file list would otherwise
silently shrink the denominator and inflate every yield computed from it.
"""

# Import Block

## Standard Python imports
import json
import os

## Kamui modules
from ..foundations import paths


def sumsFile():
    return os.path.join(paths.NORM_DIR, "generatorSums.json")


def loadSums():
    """Every recorded generator sum, keyed by sample name."""
    p = sumsFile()
    if not os.path.isfile(p):
        return {"_doc": "Generator event counts and weight sums for the full dataset, used as the normalization denominator.",
                "samples": {}}
    with open(p) as f:
        return json.load(f)


def measureFromNano(fileNames, redirector="root://cms-xrd-global.cern.ch/"):
    """Sum the generator counters in the Runs tree of a central NanoAOD dataset."""
    try:
        import ROOT
    except ImportError:
        raise RuntimeError("reading central NanoAOD needs ROOT, so run this from a cmsenv shell")
    ROOT.gErrorIgnoreLevel = ROOT.kError

    count = 0
    sumw = 0.0
    sumw2 = 0.0
    unreadable = []
    for name in fileNames:
        handle = ROOT.TFile.Open(redirector + name)
        if not handle or handle.IsZombie():
            unreadable.append(name)
            continue
        runs = handle.Get("Runs")
        for entry in runs:
            count += int(entry.genEventCount)
            sumw += float(entry.genEventSumw)
            sumw2 += float(entry.genEventSumw2)
        handle.Close()
    ## A missing file makes the sum too small, and a denominator that is too small inflates
    ## every yield, so an incomplete read is reported rather than returned as a number.
    if unreadable:
        raise RuntimeError(f"could not read {len(unreadable)} of {len(fileNames)} NanoAOD file(s); first: {unreadable[0]}")
    return {"genEvents": count, "sumGenWeight": sumw, "sumGenWeight2": sumw2}


def record(sampleName, measured=None, genEvents=None, write=True):
    """
    Assemble what is known about a sample's normalization, and store it when asked.

    Only the dataset as generated is stored: the event count and the generator weight sums,
    both read from its central NanoAOD. Nothing about what we processed belongs here. With write
    False the entry is returned for display and the file on disk is left alone.
    """
    data = loadSums()
    entry = dict(data["samples"].get(sampleName, {}))
    if measured:
        entry["sumGenWeight"] = measured["sumGenWeight"]
        entry["sumGenWeight2"] = measured["sumGenWeight2"]
    if genEvents:
        entry["genEvents"] = genEvents
    data["samples"][sampleName] = {k: entry[k] for k in ("genEvents", "sumGenWeight", "sumGenWeight2") if k in entry}
    if not write:
        return entry

    os.makedirs(paths.NORM_DIR, exist_ok=True)
    tmp = sumsFile() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, sumsFile())
    return entry


def generatedEvents(sampleName):
    """The generated event count of the whole dataset, or None when it was never recorded."""
    return loadSums()["samples"].get(sampleName, {}).get("genEvents")


def missingSums(sampleNames):
    """Samples with no generated event count recorded, and samples still lacking a weight sum."""
    data = loadSums()["samples"]
    noCount = [n for n in sampleNames if not data.get(n, {}).get("genEvents")]
    noSumw = [n for n in sampleNames if "sumGenWeight" not in data.get(n, {})]
    return noCount, noSumw


def denominator(sampleName):
    """The sum of generator weights to divide by, or None when the sample has not been measured."""
    entry = loadSums()["samples"].get(sampleName)
    if not entry or "sumGenWeight" not in entry:
        return None
    return entry["sumGenWeight"]
