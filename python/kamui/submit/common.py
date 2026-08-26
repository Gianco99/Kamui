"""
Shared machinery both submission backends use to build a job area.
"""

# Import Block

## Standard Python imports
import datetime
import getpass
import json
import os
import subprocess
import sys

## Kamui modules
from ..foundations import paths
from ..configReaders.content import resolveContent


def taskDir(taskName, create=True):
    d = os.path.join(paths.JOBS_DIR, taskName)
    if create:
        os.makedirs(d, exist_ok=True)
    return d


# A task area holds the record of what was submitted, so overwriting one destroys the provenance of jobs that may still be running.
def resolveTaskDir(taskName, assumeYes=False):
    """Pick the directory for a new task, asking before reusing an occupied one. Returns (path, name)."""
    d = os.path.join(paths.JOBS_DIR, taskName)
    if not os.path.isdir(d) or not os.listdir(d):
        return taskDir(taskName), taskName

    print(f"task '{taskName}' already has a job area at {d}")
    if assumeYes:
        answer = "y"
    elif sys.stdin.isatty():
        answer = input("  overwrite it, losing the record of what was submitted? [y/N] ").strip().lower()
    else:
        # Nothing is attached to answer, and silently overwriting a real submission's record is the one outcome to avoid.
        answer = "n"
    if answer.startswith("y"):
        print(f"  overwriting {d}")
        return taskDir(taskName), taskName

    n = 2
    while os.path.isdir(os.path.join(paths.JOBS_DIR, f"{taskName}_{n}")):
        n += 1
    newName = f"{taskName}_{n}"
    print(f"  writing to {newName} instead")
    return taskDir(newName), newName


def writeResolvedContent(d, presetName, isMC):
    """Flatten a content preset into the job area and return its path."""
    resolved = resolveContent(presetName, isMC=isMC)
    suffix = "mc" if isMC else "data"
    out = os.path.join(d, f"{presetName}.{suffix}.json")
    with open(out, "w") as f:
        json.dump(resolved, f, indent=2)
    return out


# Which commit produced a task. Ntuples outlive the working tree they came from, so a task that cannot be traced back to a revision cannot be explained later.
def _provenance():
    def git(*a):
        try:
            r = subprocess.run(["git", "-C", paths.REPO_DIR] + list(a), capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    dirty = git("status", "--porcelain")
    return {
        "submittedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "submittedBy": getpass.getuser(),
        "commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(dirty) if dirty is not None else None,
        "repo": paths.REPO_DIR,
    }


# Everything needed to explain a set of ntuples: what was asked for, what it resolved to, and the revision that did the resolving.
def writeTaskRecord(d, record, samples=None, sites=None, resolvedContent=None):
    record = dict(record)
    record["provenance"] = _provenance()
    if sites is not None:
        record["cmssw"] = sites["cmssw"]
    if samples is not None:
        record["sampleDetails"] = [{
            "name": s["name"],
            "dataset": s["dataset"],
            "dasInstance": s.get("dasInstance"),
            "isMC": bool(s["isMC"]),
            "era": s.get("era"),
            "content": s["content"],
            "lumiMask": s.get("lumiMask"),
        } for s in samples]
    if resolvedContent:
        record["resolvedContent"] = {os.path.basename(v): json.load(open(v)) for v in sorted(set(resolvedContent))}
    with open(os.path.join(d, "task.json"), "w") as f:
        json.dump(record, f, indent=2)


# Put the record next to the ntuples on EOS. The job area is gitignored local scratch; EOS is where the outputs actually live.
def publishRecord(d, sites, taskName):
    dest = "/".join([sites["eosRedirector"].rstrip("/"), sites["stageoutBase"].rstrip("/"), "ntuples", taskName])
    src = os.path.join(d, "task.json")
    if not os.path.isfile(src):
        return False
    try:
        subprocess.run(["xrdfs", sites["eosRedirector"].rstrip("/"), "mkdir", "-p", "/".join([sites["stageoutBase"].rstrip("/"), "ntuples", taskName])], capture_output=True, text=True, timeout=120)
        r = subprocess.run(["xrdcp", "-f", src, dest + "/task.json"], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  warning: could not publish task.json to EOS ({e})")
        return False
    if r.returncode != 0:
        print(f"  warning: could not publish task.json to EOS: {r.stderr.strip().splitlines()[-1:] or r.returncode}")
        return False
    print(f"  wrote provenance to {dest}/task.json")
    return True


def chunk(items, n):
    """Split `items` into lists of at most n entries."""
    return [items[i:i + n] for i in range(0, len(items), n)]
