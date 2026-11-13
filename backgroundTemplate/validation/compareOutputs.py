"""
Checks that two sets of 2v_from_jets outputs are bit-identical, histogram by histogram.

Usage: python3 compareOutputs.py <referenceDir> <candidateDir> [<fileGlob>]

Compares every TH1 in each file of the reference folder with the same-named file in the candidate folder: binning, contents and errors including under- and overflow, all exactly. Histograms named h_2v_* are never read, since in data they could hold signal-region events. Exits nonzero when anything differs or is missing.
"""

# Import Block

## Standard Python imports
import glob
import os
import sys

## Third-party imports
import numpy as np
import uproot

refDir, candDir = sys.argv[1], sys.argv[2]
pattern = sys.argv[3] if len(sys.argv) > 3 else "2v_from_jets_*.root"

bad = 0
files = sorted(glob.glob(os.path.join(refDir, pattern)))
if not files:
    sys.exit(f"No files matching {pattern} in {refDir}")
for refPath in files:
    name = os.path.basename(refPath)
    candPath = os.path.join(candDir, name)
    if not os.path.exists(candPath):
        print(f"MISSING  {name}")
        bad += 1
        continue
    ref, cand = uproot.open(refPath), uproot.open(candPath)
    refNames = {k.split(";")[0] for k, c in ref.classnames().items() if c.startswith("TH") and not k.startswith("h_2v")}
    candNames = {k.split(";")[0] for k, c in cand.classnames().items() if c.startswith("TH") and not k.startswith("h_2v")}
    differ = []
    for h in sorted(refNames & candNames):
        a, b = ref[h], cand[h]
        sameAxes = all(np.array_equal(x.edges(), y.edges()) for x, y in zip(a.axes, b.axes))
        if not (sameAxes and np.array_equal(a.values(flow=True), b.values(flow=True)) and np.array_equal(a.errors(flow=True), b.errors(flow=True))):
            differ.append(h)
    onlyRef, onlyCand = sorted(refNames - candNames), sorted(candNames - refNames)
    status = "OK      " if not (differ or onlyRef or onlyCand) else "DIFFERS "
    bad += status != "OK      "
    print(f"{status} {name}: {len(refNames & candNames)} histograms compared" + (f", differ {differ}" if differ else "") + (f", only in reference {onlyRef}" if onlyRef else "") + (f", only in candidate {onlyCand}" if onlyCand else ""))
sys.exit(1 if bad else 0)
