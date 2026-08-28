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


# The Runs counters hold the generator totals for the whole production and do not shrink when a
# selection runs, so summing the per-event weight in Events is the only way to learn what a
# processed sample is worth. The two answers differ, and using the wrong one silently returns
# the denominator instead of the processed sum.
def measureProcessed(inputPaths):
    """Sum the per-event generator weight actually present in a set of ntuples."""
    count = 0
    sumw = 0.0
    scratch = os.path.join(tempfile.gettempdir(), "kamuiNormInputs")
    for path in inputPaths:
        local, isCopy = _localCopy(path, scratch)
        with uproot.open(local) as f:
            if "Events" not in [k.split(";")[0] for k in f.keys()]:
                continue
            events = f["Events"]
            count += int(events.num_entries)
            if "genWeight" in events.keys():
                sumw += float(ak.sum(events["genWeight"].array()))
        if isCopy:
            os.remove(local)
    return {"nEvents": count, "sumWeight": sumw}


# ROOT reads xrootd natively, which uproot cannot do here, and the Runs tree is small enough
# that opening a remote NanoAOD file to read it costs seconds rather than a download.
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
    return {"nEvents": count, "sumGenWeight": sumw, "sumGenWeight2": sumw2}


def record(sampleName, measured=None, dasEvents=None, source="", write=True):
    """
    Assemble what is known about a sample's normalization, and store it when asked.

    DAS gives the generated event count as soon as a sample is added, so that much can be
    recorded immediately. The sum of generator weights needs the files themselves and is
    filled in later, once a complete production exists. With write False the entry is
    returned for display and the file on disk is left alone.
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
    if not write:
        return entry

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
