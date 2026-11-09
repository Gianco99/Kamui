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
import tarfile

## Kamui modules
from ..foundations import paths
from ..configReaders.content import resolveContent
from ..configReaders.sites import globalTag


## Characters a task name may use
TASK_NAME_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")


def checkTaskName(taskName):
    """Reject a task name that would escape the job area, the EOS path, or the shell."""
    if not TASK_NAME_OK.fullmatch(taskName or ""):
        raise ValueError(f"Bad task name {taskName!r}. Use letters, digits, dot, dash and underscore, starting with a letter or digit, at most 96 characters.")
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


def outputDir(base, taskName, stage="ntuples"):
    """Where a task writes on EOS: `<base>/<stage>/<task>`."""
    return "/".join([base.rstrip("/"), stage, taskName])


def recordedOutputDir(record):
    """The EOS output directory a task record names. Older records name it outDirBase (condor) or outLFNDirBase (CRAB)."""
    return record.get("outputDir") or record.get("outDirBase") or record.get("outLFNDirBase")


def eosListing(redirector, directory):
    """Basenames present in an EOS directory, empty if it does not exist yet."""
    try:
        r = subprocess.run(["xrdfs", redirector, "ls", directory], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"Could not list {directory}: {e}")
    if r.returncode != 0:
        ## Only a missing directory means no outputs; treating any other error as empty would resubmit finished jobs.
        if "no such file or directory" in r.stderr.lower():
            return set()
        raise RuntimeError(f"Could not list {directory}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
    return {os.path.basename(line) for line in r.stdout.split() if line.strip()}


# select reads a task's EOS folder by name, so jobs written into a used one would be read together with the earlier output.
def checkOutputUnused(sites, directory, taskName):
    """Refuse an EOS output directory that already holds anything."""
    try:
        found = eosListing(sites["eosRedirector"].rstrip("/"), directory)
    except RuntimeError as e:
        raise RuntimeError(f"Could not check that the task's EOS output directory is unused. {e}")
    if found:
        raise ValueError(f"{directory} on EOS already holds output from an earlier task named '{taskName}', and new output would mix with it. Choose a new --task.")


def _refuseSubmitted(d, taskName):
    """Refuse a job area whose crab/ directory or task.json shows that its jobs were sent."""
    try:
        record = readTaskRecord(d)
    except FileNotFoundError:
        record = {}
    except (OSError, ValueError) as e:
        raise ValueError(f"Could not read {os.path.join(d, 'task.json')} ({e}), so kamui cannot tell whether task '{taskName}' was submitted. Use a different --task.")
    if os.path.isdir(os.path.join(d, "crab")):
        retry = f" To retry the samples whose crab submit failed, run ./kamui resubmit --task {taskName}." if record.get("failedSubmissions") else ""
        raise ValueError(f"Task '{taskName}' has a CRAB work area at {os.path.join(d, 'crab')}, so its jobs may still be running. Use a different --task.{retry}")
    if record.get("condorCluster"):
        raise ValueError(f"Task '{taskName}' was submitted to condor cluster {record['condorCluster']}, so its jobs may still be running. Use a different --task.")


# A task area holds the record of what was submitted, so overwriting one destroys the provenance of jobs that may still be running.
def resolveTaskDir(taskName, sites, eosDir):
    """The job area for a new task. Refuses a task that was submitted or whose EOS output directory holds files, and reuses an area that was never submitted, such as one a dry run left."""
    checkTaskName(taskName)
    d = os.path.join(paths.JOBS_DIR, taskName)
    if os.path.islink(d):
        raise ValueError(f"{d} is a symlink, so writing there would leave the job area. Remove it first.")
    reuse = os.path.isdir(d) and bool(os.listdir(d))
    ## Every check runs before anything is cleared, so a refused task loses nothing
    if reuse:
        _refuseSubmitted(d, taskName)
    checkOutputUnused(sites, eosDir, taskName)
    if reuse:
        print(f"  Reusing the job area {d}, since its task was never submitted")
        try:
            for entry in os.listdir(d):         # Clear the contents so stale configs cannot be submitted alongside the new ones.
                full = os.path.join(d, entry)
                shutil.rmtree(full) if os.path.isdir(full) and not os.path.islink(full) else os.remove(full)
        except OSError as e:
            raise ValueError(f"Could not clear {d}: {e}")
    return taskDir(taskName)


def _contentBody(resolved):
    return {k: v for k, v in resolved.items() if k != "name"}


def contentStem(presetName):
    stem = os.path.basename(presetName.rstrip("/")) or presetName
    return stem[:-5] if stem.endswith(".json") else stem


def globalTagArg(contentJson, era, isMC, sites):
    """The `globalTag=` argument a job needs."""
    with open(contentJson) as f:
        if not json.load(f).get("needsConditions"):
            return ""
    return globalTag(era, isMC, sites)


def writeResolvedContent(d, presetName, isMC, era):
    """Flatten a content preset into the job area and return its path."""
    resolved = resolveContent(presetName, isMC=isMC, era=era)
    suffix = "mc" if isMC else "data"
    stem = contentStem(presetName)
    ## A preset resolves against its era's content set
    out = os.path.join(d, f"{stem}.{suffix}.{era}.json")
    if os.path.exists(out) and _contentBody(json.load(open(out))) != _contentBody(resolved):
        raise ValueError(f"Two different content presets both resolve to '{stem}'; rename one or use their plain names")
    with open(out, "w") as f:
        json.dump(resolved, f, indent=2)
    return out


# Which commit produced a task, since ntuples outlive the working tree they came from.
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
    _saveRecord(d, record)


def _saveRecord(d, record):
    """Write task.json through a temporary file, so a failure partway cannot destroy the record."""
    out = os.path.join(d, "task.json")
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(record, f, indent=2)
    os.replace(tmp, out)


def readTaskRecord(d):
    """The task.json of a job area."""
    with open(os.path.join(d, "task.json")) as f:
        return json.load(f)


def updateTaskRecord(d, fields):
    """Set fields in a job area's task.json, keeping everything else it records."""
    record = readTaskRecord(d)
    record.update(fields)
    _saveRecord(d, record)


def outputBase(sites, backend, override=None):
    if override:
        return override.rstrip("/")
    key = "crabStageoutBase" if backend == "crab" else "stageoutBase"
    return sites[key].rstrip("/")


# Put the record next to the output on EOS, since the job area is gitignored scratch.
def publishRecord(d, sites, taskName, base=None, stage="ntuples"):
    """Copy a job area's task.json to `<base>/<stage>/<task>` on EOS. Returns whether the copy worked."""
    directory = outputDir(base or sites["stageoutBase"], taskName, stage)
    dest = sites["eosRedirector"].rstrip("/") + "/" + directory
    src = os.path.join(d, "task.json")
    if not os.path.isfile(src):
        return False
    try:
        subprocess.run(["xrdfs", sites["eosRedirector"].rstrip("/"), "mkdir", "-p", directory], capture_output=True, text=True, timeout=120)
        r = subprocess.run(["xrdcp", "-f", src, dest + "/task.json"], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  Warning: could not publish task.json to EOS ({e})")
        return False
    if r.returncode != 0:
        print(f"  Warning: could not publish task.json to EOS: {r.stderr.strip().splitlines()[-1:] or r.returncode}")
        return False
    print(f"  Wrote provenance to {dest}/task.json")
    return True


## The parts of a CMSSW area that jobs need, the same ones CRAB ships: compiled libraries with their plugin caches, and the python CMSSW generates for them
AREA_PARTS = ("lib", "python", "cfipython")
## Source files whose change needs a new scram b
BUILD_SOURCES = (".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".xml")
## The condor job's copy of the compiled code
AREA_TARBALL = "cmsswArea.tar.gz"
## The ntuple code a job runs, from ntupleProduction/cmssw/
NTUPLE_CODE = ("ntuple_cfg.py", "ntupleTables.py")


# Jobs run the plugins compiled in the CMSSW area kamui runs from, so a source edited after the last scram b would go out as the old build without anyone noticing.
def checkLocalArea(cmsswVersion=None, scramArch=None):
    """The CMSSW area kamui runs from. Refuses when there is none, when it differs from the release the jobs run, or when a source is newer than its compiled libraries."""
    base = os.environ.get("CMSSW_BASE")
    if not base or not os.path.isdir(base):
        raise RuntimeError("No CMSSW area: run kamui from the cmsenv shell of the CMSSW area that holds the vertexing build")
    if cmsswVersion and (os.environ.get("CMSSW_VERSION"), os.environ.get("SCRAM_ARCH")) != (cmsswVersion, scramArch):
        raise RuntimeError(f"The jobs run {cmsswVersion} ({scramArch}) from config/sites.json, but kamui runs in {os.environ.get('CMSSW_VERSION')} ({os.environ.get('SCRAM_ARCH')}), so the compiled plugins would not fit. Run kamui from a {cmsswVersion} area.")
    libDir = os.path.join(base, "lib", os.environ.get("SCRAM_ARCH", ""))
    libs = [os.path.join(libDir, f) for f in os.listdir(libDir) if f.endswith(".so")] if os.path.isdir(libDir) else []
    sources = []
    for root, dirs, files in os.walk(os.path.join(base, "src"), followlinks=True):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        sources += [os.path.join(root, f) for f in files if f.endswith(BUILD_SOURCES)]
    if sources and not libs:
        raise RuntimeError(f"The code in {base}/src was never built: run scram b there first")
    if sources:
        newest = max(sources, key=os.path.getmtime)
        if os.path.getmtime(newest) > min(os.path.getmtime(x) for x in libs):
            raise RuntimeError(f"{newest} changed after the last build, so the jobs would run the old code: run scram b in {base}/src first")
    return base


def packLocalArea(d, base):
    """Pack the compiled code of a CMSSW area into the job area, for condor workers that start from a fresh release. Returns the tarball path."""
    out = os.path.join(d, AREA_TARBALL)
    with tarfile.open(out, "w:gz") as tar:
        for part in AREA_PARTS:
            p = os.path.join(base, part)
            if os.path.isdir(p):
                tar.add(p, arcname=part, filter=lambda t: None if "__pycache__" in t.name else t)
    return out


# Condor sends a job its inputs only when it starts, and resubmit sends jobs again later, so every job of a task runs these copies taken at submit.
def copyNtupleCode(d):
    """Copy the ntuple code into the job area. Returns the paths of the copies, in NTUPLE_CODE order."""
    return [shutil.copy2(os.path.join(paths.CMSSW_DIR, f), d) for f in NTUPLE_CODE]


def chunk(items, n):
    """Split `items` into lists of at most n entries."""
    return [items[i:i + n] for i in range(0, len(items), n)]
