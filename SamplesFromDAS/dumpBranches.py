#!/usr/bin/env python3
"""
Run edmDumpEventContent on the first EOS file for each sample and record the output.

Requires the same CMSSW environment as fetchSamples.py:
    source /cvmfs/cms.cern.ch/cmsset_default.sh
    cd /uscms/home/gdecastr/nobackup/work/CMSSW_14_1_0_pre4/src/
    cmsenv

Output txt files are written to SamplesFromDAS/branchDumps/<sampleName>.txt

Usage:
  python3 dumpBranches.py [--config samples.json] [--sample NAME] [--no-save]
"""

import argparse
import json
import os
import subprocess
import sys


DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "branchDumps")


def getEosFiles(eosRedirector, outputEosDir, sampleName):
    """List files already copied to EOS for this sample."""
    eosPath = f"{outputEosDir}/{sampleName}"
    result = subprocess.run(
        ["xrdfs", eosRedirector, "ls", eosPath],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]


def runEdmDump(lfn, eosRedirector):
    url = f"{eosRedirector}/{lfn}"
    result = subprocess.run(
        ["edmDumpEventContent", url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout, None


def main():
    parser = argparse.ArgumentParser(description="Dump MiniAOD branches via edmDumpEventContent")
    parser.add_argument("--config", default="samples.json", help="Path to samples JSON config")
    parser.add_argument("--sample", default=None, help="Only process the sample with this name")
    parser.add_argument("--no-save", dest="noSave", action="store_true", help="Print only, do not write txt files")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    eosRedirector  = cfg["eosRedirector"].rstrip("/")
    outputEosDir   = cfg["outputEosDir"].rstrip("/")
    samples        = cfg["samples"]

    if args.sample:
        samples = [s for s in samples if s["name"] == args.sample]
        if not samples:
            sys.exit(f"No sample named '{args.sample}' found in config.")

    if not args.noSave:
        os.makedirs(DUMP_DIR, exist_ok=True)

    for sample in samples:
        name = sample["name"]
        print(f"\n{'='*60}")
        print(f"Sample: {name}")

        lfns = getEosFiles(eosRedirector, outputEosDir, name)
        if not lfns:
            print("  No files found on EOS for this sample — run fetchSamples.py first.")
            continue

        firstLfn = lfns[0]
        print(f"  File : {eosRedirector}/{firstLfn}")
        print(f"  Running edmDumpEventContent...")

        content, err = runEdmDump(firstLfn, eosRedirector)
        if err:
            print(f"  ERROR: {err}")
            continue

        print(content)

        if not args.noSave:
            outPath = os.path.join(DUMP_DIR, f"{name}.txt")
            with open(outPath, "w") as f:
                f.write(f"Sample : {name}\n")
                f.write(f"File   : {eosRedirector}/{firstLfn}\n")
                f.write("="*60 + "\n")
                f.write(content)
            print(f"  Saved to {outPath}")


if __name__ == "__main__":
    main()
