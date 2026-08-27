"""
Shared machinery both submission backends use to build a job area.
"""

# Import Block

## Standard Python imports
import datetime
import errno
import getpass
import json
import os
import re
import shutil
import subprocess
import sys

## Kamui modules
from ..foundations import paths
from ..configReaders.content import resolveContent


## Characters a task name may use
TASK_NAME_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")


def checkTaskName(taskName):
    """Reject a task name that would escape the job area, the EOS path, or the shell."""
    if not TASK_NAME_OK.fullmatch(taskName or ""):
        raise ValueError(
            f"bad task name {taskName!r}. Use letters, digits, dot, dash and underscore, "
            "starting with a letter or digit, at most 96 characters."
        )
    return taskName


def runTool(cmd, **kw):
    cmd = list(cmd)
    try:
        return subprocess.run(cmd, **kw)
    except OSError as e:
        if e.errno != errno.ENOEXEC:
            raise
        full = shutil.which(cmd[0])
        if full is None:
            raise
        return subprocess.run(["/bin/sh", full] + cmd[1:], **kw)


def taskDir(taskName, create=True):
    checkTaskName(taskName)
    d = os.path.join(paths.JOBS_DIR, taskName)
    if create:
        os.makedirs(d, exist_ok=True)
    return d


# A task area holds the record of what was submitted, so overwriting one destroys the provenance of jobs that may still be running.
def resolveTaskDir(taskName, assumeYes=False):
    """Pick the directory for a new task, asking before reusing an occupied one. Returns (path, name)."""
    checkTaskName(taskName)
    d = os.path.join(paths.JOBS_DIR, taskName)
    if os.path.islink(d):
        raise ValueError(f"{d} is a symlink, so writing there would leave the job area. Remove it first.")
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
        if os.path.isdir(os.path.join(d, "crab")):
            raise ValueError(
                f"task '{taskName}' has a CRAB work area at {os.path.join(d, 'crab')}, so its jobs may still be running. "
                "Use a different --task, or remove that directory yourself once the task is finished."
            )
        record = os.path.join(d, "task.json")
        if os.path.isfile(record):
            try:
                with open(record) as f:
                    cluster = json.load(f).get("condorCluster")
            except (OSError, ValueError):
                cluster = None
            if cluster:
                raise ValueError(
                    f"task '{taskName}' was submitted to condor cluster {cluster}, so its jobs may still be running. "
                    "Use a different --task, or remove that directory yourself once the task is finished."
                )
        print(f"  overwriting {d}")
        try:
            for entry in os.listdir(d):         # Clear the contents so stale configs cannot be submitted alongside the new ones.
                full = os.path.join(d, entry)
                shutil.rmtree(full) if os.path.isdir(full) and not os.path.islink(full) else os.remove(full)
        except OSError as e:
            raise ValueError(f"could not clear {d}: {e}")
        return taskDir(taskName), taskName

    n = 2
    stem = taskName
    while len(f"{stem}_{n}") > 96:
        stem = stem[:-1]
    while os.path.isdir(os.path.join(paths.JOBS_DIR, f"{stem}_{n}")):
        n += 1
        while len(f"{stem}_{n}") > 96:
            stem = stem[:-1]
    newName = f"{stem}_{n}"
    checkTaskName(newName)
    print(f"  writing to {newName} instead")
    return taskDir(newName), newName


def _contentBody(resolved):
    return {k: v for k, v in resolved.items() if k != "name"}


def contentStem(presetName):
    stem = os.path.basename(presetName.rstrip("/")) or presetName
    return stem[:-5] if stem.endswith(".json") else stem


def writeResolvedContent(d, presetName, isMC):
    """Flatten a content preset into the job area and return its path."""
    resolved = resolveContent(presetName, isMC=isMC)
    suffix = "mc" if isMC else "data"
    stem = contentStem(presetName)
    out = os.path.join(d, f"{stem}.{suffix}.json")
    if os.path.exists(out) and _contentBody(json.load(open(out))) != _contentBody(resolved):
        raise ValueError(f"two different content presets both resolve to '{stem}'; rename one or use their plain names")
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
    out = os.path.join(d, "task.json")
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(record, f, indent=2)
    os.replace(tmp, out)


# Put the record next to the ntuples on EOS. The job area is gitignored local scratch; EOS is where the outputs actually live.
def outputBase(sites, backend, override=None):
    if override:
        return override.rstrip("/")
    key = "crabStageoutBase" if backend == "crab" else "stageoutBase"
    return sites[key].rstrip("/")


def publishRecord(d, sites, taskName, base=None):
    base = (base or sites["stageoutBase"]).rstrip("/")
    dest = "/".join([sites["eosRedirector"].rstrip("/"), base, "ntuples", taskName])
    src = os.path.join(d, "task.json")
    if not os.path.isfile(src):
        return False
    try:
        subprocess.run(["xrdfs", sites["eosRedirector"].rstrip("/"), "mkdir", "-p", "/".join([base, "ntuples", taskName])], capture_output=True, text=True, timeout=120)
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
