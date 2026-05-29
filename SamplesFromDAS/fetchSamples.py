#!/usr/bin/env python3
"""
Query DAS for MiniAOD files listed in samples.json and copy them to EOS.

Requires CMSSW environment and voms proxy:
    source /cvmfs/cms.cern.ch/cmsset_default.sh
    cd /uscms/home/gdecastr/nobackup/work/CMSSW_14_1_0_pre4/src/
    cmsenv
    voms-proxy-init --voms cms

Usage:
  python3 fetchSamples.py [--config samples.json] [--dry-run] [--sample NAME]
"""

import argparse
import json
import os
import subprocess
import sys


def runDasgoclient(dasName, dasInstance):
    cmd = [
        "dasgoclient",
        f"--query=file dataset={dasName} instance={dasInstance}",
        "--limit=0",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR querying DAS: {result.stderr.strip()}")
        return []
    return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]


def copyFile(lfn, destDir, sourceRedirector, eosRedirector, dryRun):
    filename = os.path.basename(lfn)
    src = f"{sourceRedirector}/{lfn}"
    dst = f"{eosRedirector}/{destDir}/{filename}"

    print(f"  {'[DRY RUN] ' if dryRun else ''}xrdcp {src} {dst}")
    if dryRun:
        return True

    result = subprocess.run(["xrdcp", "-f", src, dst], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED: {result.stderr.strip()}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Fetch MiniAOD files from DAS to EOS")
    parser.add_argument("--config", default="samples.json", help="Path to samples JSON config")
    parser.add_argument("--dry-run", dest="dryRun", action="store_true", help="Print commands without executing")
    parser.add_argument("--sample", default=None, help="Only process the sample with this name")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    outputEosDir    = cfg["outputEosDir"].rstrip("/")
    eosRedirector   = cfg["eosRedirector"].rstrip("/")
    sourceRedirector = cfg["sourceRedirector"].rstrip("/")
    samples         = cfg["samples"]

    if args.sample:
        samples = [s for s in samples if s["name"] == args.sample]
        if not samples:
            sys.exit(f"No sample named '{args.sample}' found in config.")

    for sample in samples:
        name        = sample["name"]
        dasName     = sample["dasName"]
        dasInstance = sample["dasInstance"]
        destDir     = f"{outputEosDir}/{name}"

        print(f"\n{'='*60}")
        print(f"Sample : {name}")
        print(f"DAS    : {dasName}")
        print(f"Dest   : {eosRedirector}/{destDir}")

        print("  Querying DAS...")
        lfns = runDasgoclient(dasName, dasInstance)
        if not lfns:
            print("  No files found, skipping.")
            continue

        nCap = sample.get("nFilesFor10k")
        if nCap is not None and len(lfns) > nCap:
            print(f"  Found {len(lfns)} file(s), capping at {nCap} (nFilesFor10k).")
            lfns = lfns[:nCap]
        else:
            print(f"  Found {len(lfns)} file(s).")

        if not args.dryRun:
            result = subprocess.run(
                ["xrdfs", eosRedirector, "mkdir", "-p", destDir],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"  WARNING: could not mkdir {destDir}: {result.stderr.strip()}")
        else:
            print(f"  [DRY RUN] xrdfs mkdir -p {destDir}")

        ok = err = 0
        for lfn in lfns:
            success = copyFile(lfn, destDir, sourceRedirector, eosRedirector, args.dryRun)
            if success:
                ok += 1
            else:
                err += 1

        print(f"  Done: {ok} copied, {err} failed.")

    print("\nAll samples processed.")


if __name__ == "__main__":
    main()
