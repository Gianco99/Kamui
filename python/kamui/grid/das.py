"""
Wraps dasgoclient and caches what it returns.
"""

# Import Block

## Standard Python imports
import hashlib
import json
import os
import shutil
import subprocess
import time

## Kamui modules
from ..foundations import paths


class DasError(RuntimeError):
    pass


def _haveDasgoclient():
    return shutil.which("dasgoclient") is not None


def _proxyTimeLeft():
    """Seconds left on the grid proxy, or None if voms-proxy-info is unavailable."""
    if shutil.which("voms-proxy-info") is None:
        return None
    r = subprocess.run(["voms-proxy-info", "-timeleft"], capture_output=True, text=True)
    if r.returncode != 0:
        return 0
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


def _requireProxy(minSeconds=3600):
    left = _proxyTimeLeft()
    if left is None:
        raise DasError("voms-proxy-info not found - did you run cmsenv?")
    if left < minSeconds:
        raise DasError(
            f"grid proxy has {left}s left (need >{minSeconds}s). Run:\n"
            "    voms-proxy-init --rfc --voms cms -valid 192:00"
        )


## How stale a cached DAS answer may be before we ask again
CACHE_MAX_AGE_DAYS = 30


def _cachePath(query, instance):
    key = hashlib.sha1(f"{instance}|{query}".encode()).hexdigest()[:16]
    return os.path.join(paths.CACHE_DIR, key + ".json")


def query(q, instance="prod/global", refresh=False, maxAgeDays=CACHE_MAX_AGE_DAYS, jsonOut=False):
    """
    Run one dasgoclient query and return its lines (or parsed JSON if jsonOut).
    Results are cached; `maxAgeDays` bounds how stale a cache entry may be.
    """
    cp = _cachePath(q + ("|json" if jsonOut else ""), instance)
    if not refresh and os.path.exists(cp):
        age = (time.time() - os.path.getmtime(cp)) / 86400.0
        if age < maxAgeDays:
            with open(cp) as f:
                return json.load(f)["result"]

    if not _haveDasgoclient():
        raise DasError("dasgoclient not on PATH - source cmsset_default.sh and cmsenv first")
    _requireProxy()

    cmd = ["dasgoclient", f"--query={q} instance={instance}", "--limit=0"]
    if jsonOut:
        cmd.append("--json")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise DasError(f"dasgoclient failed for '{q}':\n{r.stderr.strip()}")

    result = json.loads(r.stdout) if jsonOut else [l.strip() for l in r.stdout.splitlines() if l.strip()]

    os.makedirs(paths.CACHE_DIR, exist_ok=True)
    with open(cp, "w") as f:
        json.dump({"query": q, "instance": instance, "when": time.time(), "result": result}, f)
    return result


def listFiles(dataset, instance="prod/global", refresh=False):
    """LFNs of a dataset, sorted for reproducible job splitting."""
    return sorted(query(f"file dataset={dataset}", instance, refresh))


def datasetSummary(dataset, instance="prod/global", refresh=False):
    """{'nfiles','nevents','sizeGB'} for a dataset, or zeros if DAS has nothing."""
    rows = query(f"summary dataset={dataset}", instance, refresh, jsonOut=True)
    for row in rows:
        for s in row.get("summary", []):
            return {
                "nfiles":  int(s.get("nfiles", 0)),
                "nevents": int(s.get("nevents", 0)),
                "sizeGB":  float(s.get("file_size", 0)) / 1e9,
            }
    return {"nfiles": 0, "nevents": 0, "sizeGB": 0.0}


def findDatasets(pattern, instance="prod/global", refresh=False):
    """Wildcard dataset search, e.g. '/*Hto2Sto4D*/Run3*Summer24*/MINIAODSIM'."""
    return sorted(query(f"dataset dataset={pattern}", instance, refresh))


def clearCache():
    """Delete every cached response."""
    if os.path.isdir(paths.CACHE_DIR):
        shutil.rmtree(paths.CACHE_DIR)


def _cacheEntries():
    if not os.path.isdir(paths.CACHE_DIR):
        return []
    out = []
    for name in sorted(os.listdir(paths.CACHE_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(paths.CACHE_DIR, name)
        try:
            with open(path) as f:
                rec = json.load(f)
        except (OSError, ValueError):
            # A truncated entry is unreadable to us and to query(), so treat it as prunable rather than crashing the report.
            out.append({"path": path, "query": None, "instance": None, "ageDays": None, "bytes": os.path.getsize(path)})
            continue
        out.append({
            "path": path,
            "query": rec.get("query"),
            "instance": rec.get("instance"),
            "ageDays": (time.time() - rec.get("when", 0)) / 86400.0,
            "bytes": os.path.getsize(path),
        })
    return out


def cacheStats(maxAgeDays=CACHE_MAX_AGE_DAYS):
    """Describe the cache: how many entries, how large, how old, how many are past their age limit."""
    entries = _cacheEntries()
    ages = [e["ageDays"] for e in entries if e["ageDays"] is not None]
    return {
        "dir": paths.CACHE_DIR,
        "n": len(entries),
        "bytes": sum(e["bytes"] for e in entries),
        "oldestDays": max(ages) if ages else None,
        "newestDays": min(ages) if ages else None,
        "nStale": sum(1 for e in entries if e["ageDays"] is None or e["ageDays"] >= maxAgeDays),
    }


def pruneCache(maxAgeDays=CACHE_MAX_AGE_DAYS):
    """Delete only the entries query() would already refuse to use. Returns how many went."""
    gone = 0
    for e in _cacheEntries():
        if e["ageDays"] is None or e["ageDays"] >= maxAgeDays:
            try:
                os.remove(e["path"])
                gone += 1
            except OSError:
                pass
    return gone
