"""
The generator sums a sample must be normalized by.

These belong to the whole dataset as it exists in DAS, not to whatever subset a job
happened to read, so they are measured once over a complete production and stored.
A skim or a capped file list would otherwise silently shrink the denominator and
inflate every yield computed from it.
"""

# Import Block

## Standard Python imports
import json
import os
import tempfile

## Third-party
import awkward as ak
import uproot

## Kamui modules
from ..foundations import paths
from .engine import _localCopy


def sumsFile():
    return os.path.join(paths.XSEC_DIR, "generatorSums.json")


def loadSums():
    """Every recorded generator sum, keyed by sample name."""
    p = sumsFile()
    if not os.path.isfile(p):
        return {"_doc": "Generator event counts and weight sums for the full dataset, used as the normalization denominator.",
                "samples": {}}
    with open(p) as f:
        return json.load(f)


def measure(inputPaths):
    """Sum the run-level generator counters over a set of ntuples."""
    count = 0
    sumw = 0.0
    sumw2 = 0.0
    scratch = os.path.join(tempfile.gettempdir(), "kamuiNormInputs")
    for p in inputPaths:
        local, isCopy = _localCopy(p, scratch)
        with uproot.open(local) as f:
            if "Runs" not in [k.split(";")[0] for k in f.keys()]:
                continue
            runs = f["Runs"]
            count += int(ak.sum(runs["genEventCount"].array()))
            sumw += float(ak.sum(runs["genEventSumw"].array()))
            if "genEventSumw2" in runs.keys():
                sumw2 += float(ak.sum(runs["genEventSumw2"].array()))
        if isCopy:
            try:
                os.remove(local)
            except OSError:
                pass
    return {"nEvents": count, "sumGenWeight": sumw, "sumGenWeight2": sumw2}


def record(sampleName, measured=None, dasEvents=None, source=""):
    """
    Store what is known about a sample's normalization.

    DAS gives the generated event count as soon as a sample is added, so that much can be
    recorded immediately. The sum of generator weights needs the files themselves and is
    filled in later, once a complete production exists.
    """
    data = loadSums()
    entry = dict(data["samples"].get(sampleName, {}))
    if measured:
        entry.update(measured)
        entry["source"] = source
    if dasEvents:
        entry["dasEvents"] = dasEvents
    if "nEvents" in entry and entry.get("dasEvents"):
        entry["complete"] = (entry["nEvents"] == entry["dasEvents"])
    data["samples"][sampleName] = entry

    os.makedirs(paths.XSEC_DIR, exist_ok=True)
    tmp = sumsFile() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, sumsFile())
    return entry


def missingSums(sampleNames):
    """Samples with no DAS event count recorded, and samples still lacking a weight sum."""
    data = loadSums()["samples"]
    noDas = [n for n in sampleNames if not data.get(n, {}).get("dasEvents")]
    noSumw = [n for n in sampleNames if "sumGenWeight" not in data.get(n, {})]
    return noDas, noSumw


def denominator(sampleName):
    """The sum of generator weights to divide by, or None when the sample has not been measured."""
    entry = loadSums()["samples"].get(sampleName)
    if not entry or "sumGenWeight" not in entry:
        return None
    if entry.get("complete") is False:
        raise ValueError(
            f"generator sums for '{sampleName}' were measured over {entry['nEvents']:,} events "
            f"but DAS has {entry['dasEvents']:,}. Re-measure over a complete production before normalizing."
        )
    return entry["sumGenWeight"]
