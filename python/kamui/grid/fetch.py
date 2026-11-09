"""
Copies MiniAOD from the grid to our EOS area.
"""

# Import Block

## Standard Python imports
import os
import re
import subprocess

## Kamui modules
from . import das
from ..configReaders.sites import loadSites


def _eosDir(sites, sampleName):
    return "/".join([sites["stageoutBase"].rstrip("/"), sites["miniaodDir"], sampleName])


## A line of `xrdfs ls -l`: the size comes right before the date and time, and the path is last
LONG_LISTING = re.compile(r"\s(\d+)\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+(\S+)$")


# A copy that died partway can leave an empty file under the right name, so only a file with bytes in it counts as staged.
def _listStaged(sites, sampleName):
    """Paths of the sample's files on EOS that are not empty."""
    try:
        r = subprocess.run(["xrdfs", sites["eosRedirector"].rstrip("/"), "ls", "-l", _eosDir(sites, sampleName)], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  Warning: could not list EOS ({e}); assuming nothing is staged")
        return []
    if r.returncode != 0:
        return []
    staged = []
    for line in r.stdout.splitlines():
        m = LONG_LISTING.search(line.strip())
        if m and int(m.group(1)) > 0:
            staged.append(m.group(2))
    return staged


def stage(sample, sites=None, maxFiles=None, dryRun=False, refresh=False):
    """Copy files for one sample, capped at maxFiles when given. Returns (nPresent, nFailed), where nPresent counts files copied, already on EOS and not empty, or listed in a dry run."""
    sites = sites or loadSites()
    dest = _eosDir(sites, sample["name"])
    eosRed = sites["eosRedirector"].rstrip("/")
    srcRed = sites["sourceRedirector"].rstrip("/")

    lfns = das.listFiles(sample["dataset"], sample["dasInstance"], refresh=refresh)
    if not lfns:
        print("  No files found in DAS")
        return 0, 0

    total = len(lfns)
    lfns = lfns[:maxFiles]
    print(f"  {total} file{'' if total == 1 else 's'} in DAS, copying {len(lfns)}")

    if dryRun:
        print(f"  [dryRun] xrdfs {eosRed} mkdir -p {dest}")
    else:
        r = subprocess.run(["xrdfs", eosRed, "mkdir", "-p", dest], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  Could not create {dest}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
            return 0, len(lfns)

    # A dry run lists EOS too, so what it prints is what a real run would copy.
    already = set(os.path.basename(f) for f in _listStaged(sites, sample["name"]))
    ok = bad = 0
    for lfn in lfns:
        fn = os.path.basename(lfn)
        if fn in already:
            print(f"  Skip (already on EOS) {fn}")
            ok += 1
            continue
        src, dst = f"{srcRed}/{lfn}", f"{eosRed}/{dest}/{fn}"
        if dryRun:
            print(f"  [dryRun] xrdcp {src} {dst}")
            ok += 1
            continue
        r = subprocess.run(["xrdcp", "-f", src, dst], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  FAILED {fn}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
            bad += 1
        else:
            print(f"  Copied {fn}")
            ok += 1
    return ok, bad
