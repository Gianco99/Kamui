"""
Copies raw MiniAOD from the grid to our EOS area.
"""

# Import Block

## Standard Python imports
import os
import subprocess

## Kamui modules
from . import das
from ..configReaders.sites import loadSites


def _eosDir(sites, sampleName):
    return "/".join([sites["stageoutBase"].rstrip("/"), sites["miniaodDir"], sampleName])


def _listStaged(sites, sampleName):
    r = subprocess.run(["xrdfs", sites["eosRedirector"].rstrip("/"), "ls", _eosDir(sites, sampleName)], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def stage(sample, sites=None, quick=True, maxFiles=None, dryRun=False, refresh=False):
    """Copy files for one sample, capped at nFilesFor10k unless quick is False. Returns (nCopied, nFailed)."""
    sites = sites or loadSites()
    dest = _eosDir(sites, sample["name"])
    eosRed = sites["eosRedirector"].rstrip("/")
    srcRed = sites["sourceRedirector"].rstrip("/")

    lfns = das.listFiles(sample["dataset"], sample["dasInstance"], refresh=refresh)
    if not lfns:
        print("  no files found in DAS")
        return 0, 0

    cap = maxFiles if maxFiles is not None else (sample.get("nFilesFor10k") if quick else None)
    total = len(lfns)
    if cap is not None and total > cap:
        lfns = lfns[:cap]
    print(f"  {total} file(s) in DAS, copying {len(lfns)}")

    if dryRun:
        print(f"  [dry-run] xrdfs {eosRed} mkdir -p {dest}")
    else:
        subprocess.run(["xrdfs", eosRed, "mkdir", "-p", dest], capture_output=True, text=True)

    # A dry run lists EOS too, so what it prints is what a real run would copy.
    already = set(os.path.basename(f) for f in _listStaged(sites, sample["name"]))
    ok = bad = 0
    for lfn in lfns:
        fn = os.path.basename(lfn)
        if fn in already:
            print(f"  skip (already on EOS) {fn}")
            ok += 1
            continue
        src, dst = f"{srcRed}/{lfn}", f"{eosRed}/{dest}/{fn}"
        if dryRun:
            print(f"  [dry-run] xrdcp {src} {dst}")
            ok += 1
            continue
        r = subprocess.run(["xrdcp", "-f", src, dst], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  FAILED {fn}: {r.stderr.strip().splitlines()[-1:]}")
            bad += 1
        else:
            print(f"  copied {fn}")
            ok += 1
    return ok, bad
