"""
Checks that two sets of 2v_from_jets outputs hold byte-identical objects, key by key.

Usage: python3 compareRaw.py <referenceDir> <candidateDir> [--mc]

For each file of the reference folder, compares the key list (names, cycles, order) and the stored, uncompressed bytes of every object with the same-named file in the candidate folder. This also covers what compareOutputs.py does not read: the f_dphi TF1, object bits, titles and statistics. In data, h_2v_* and the canvas (which holds a copy of h_2v_sumdbv) are never read; --mc compares them too. Exits nonzero when anything differs or is missing.
"""

# Import Block

## Standard Python imports
import glob
import os
import sys

## Third-party imports
import uproot

refDir, candDir = sys.argv[1], sys.argv[2]
mc = "--mc" in sys.argv[3:]

bad = 0
files = sorted(glob.glob(os.path.join(refDir, "2v_from_jets_*.root")))
if not files:
    sys.exit(f"No 2v_from_jets_*.root files in {refDir}")
for refPath in files:
    name = os.path.basename(refPath)
    candPath = os.path.join(candDir, name)
    if not os.path.exists(candPath):
        print(f"MISSING  {name}")
        bad += 1
        continue
    ref, cand = uproot.open(refPath), uproot.open(candPath)
    keys = ref.keys(cycle=True, recursive=False)
    problems = [] if keys == cand.keys(cycle=True, recursive=False) else ["key list differs"]
    compared = 0
    for k in keys:
        if not mc and k.startswith(("h_2v", "c_sumdbv")):
            continue
        payloads = []
        for f in (ref, cand):
            key = f.key(k)
            chunk, cursor = key.get_uncompressed_chunk_cursor()
            payloads.append(chunk.raw_data.tobytes()[cursor.index:cursor.index + key.data_uncompressed_bytes])
        compared += 1
        if payloads[0] != payloads[1]:
            problems.append(k)
    bad += bool(problems)
    print(("OK       " if not problems else "DIFFERS  ") + f"{name}: {compared} stored objects compared" + (f", differ {problems}" if problems else ""))
sys.exit(1 if bad else 0)
