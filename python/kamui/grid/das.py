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


def _cachePath(query, instance, jsonOut=False):
    key = hashlib.sha1(json.dumps([instance, query, bool(jsonOut)]).encode()).hexdigest()[:16]
    return os.path.join(paths.CACHE_DIR, key + ".json")


def query(q, instance="prod/global", refresh=False, maxAgeDays=CACHE_MAX_AGE_DAYS, jsonOut=False):
    """
    Run one dasgoclient query and return its lines (or parsed JSON if jsonOut).
    Results are cached; `maxAgeDays` bounds how stale a cache entry may be.
    """
    cp = _cachePath(q, instance, jsonOut)
    if not refresh and os.path.exists(cp):
        age = (time.time() - os.path.getmtime(cp)) / 86400.0
        if 0 <= age < maxAgeDays:
            try:
                with open(cp) as f:
                    rec = json.load(f)
                if isinstance(rec, dict) and "result" in rec and rec["result"] is not None:
                    return rec["result"]
            except (OSError, ValueError):
                pass                            # Unreadable entry, so treat it as a miss and ask DAS again.

    if not _haveDasgoclient():
        raise DasError("dasgoclient not on PATH - source cmsset_default.sh and cmsenv first")
    _requireProxy()

    cmd = ["dasgoclient", f"--query={q} instance={instance}", "--limit=0"]
    if jsonOut:
        cmd.append("--json")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise DasError(f"dasgoclient failed for '{q}':\n{r.stderr.strip()}")

    try:
        result = json.loads(r.stdout) if jsonOut else [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except ValueError as e:
        raise DasError(f"dasgoclient returned unparseable JSON for '{q}':\n{e}")

    if not result and r.stderr.strip():
        print(f"  warning: dasgoclient returned nothing for '{q}' and said: {r.stderr.strip().splitlines()[-1]}")
        return result

    os.makedirs(paths.CACHE_DIR, exist_ok=True)
    tmp = cp + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump({"query": q, "instance": instance, "jsonOut": bool(jsonOut), "when": time.time(), "result": result}, f)
        os.replace(tmp, cp)                     # Atomic, so an interrupted query cannot leave a broken entry.
    except OSError:
        pass                                    # A cache that cannot be written is a cache miss next time, never a failure now.
    return result


def listFiles(dataset, instance="prod/global", refresh=False):
    """LFNs of a dataset, deduplicated and sorted for reproducible job splitting."""
    return sorted(set(query(f"file dataset={dataset}", instance, refresh)))


def datasetSummary(dataset, instance="prod/global", refresh=False):
    """{'nfiles','nevents','sizeGB'} for a dataset, or zeros if DAS has nothing."""
    rows = query(f"summary dataset={dataset}", instance, refresh, jsonOut=True)
    def num(v, cast):
        try:
            return cast(v)
        except (TypeError, ValueError):
            return cast(0)
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        for s in row.get("summary") or []:
            if not isinstance(s, dict):
                continue
            return {
                "nfiles":  num(s.get("nfiles", 0), int),
                "nevents": num(s.get("nevents", 0), int),
                "sizeGB":  num(s.get("file_size", 0), float) / 1e9,
            }
    return {"nfiles": 0, "nevents": 0, "sizeGB": 0.0}


# The generator weight sum is not in DAS: it is a property of the event payload, so nobody
# records it centrally. Central NanoAOD carries it in the Runs tree, so the denominator comes
# from the NanoAOD sibling of whatever MiniAOD a sample names.
def nanoSibling(dataset, instance="prod/global", refresh=False):
    """The central NanoAOD dataset matching a MiniAOD one, or None when no match is unambiguous."""
    primary, processed = dataset.strip("/").split("/")[:2]
    if "MiniAOD" not in processed:
        return None
    campaign = processed.split("MiniAOD")[0]                  # RunIISummer20UL18
    conditions = processed.split("-", 1)[1] if "-" in processed else ""   # 106X_..._L1v1-v2

    found = findDatasets(f"/{primary}/*/NANOAODSIM", instance=instance, refresh=refresh)
    ## The campaign pins the era and the conditions tag pins the reprocessing, so a Run 2
    ## sample can never pick up its own Run 3 twin or a different global tag.
    matches = [d for d in found
               if d.strip("/").split("/")[1].startswith(campaign)
               and (not conditions or conditions in d.strip("/").split("/")[1])]
    if not matches:
        return None
    ## Several NanoAOD versions of one campaign exist; the newest is the one to trust.
    return sorted(matches)[-1]


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
        if not (name.endswith(".json") or name.endswith(".json.tmp")):
            continue
        path = os.path.join(paths.CACHE_DIR, name)
        try:
            size = os.path.getsize(path)
        except OSError:
            continue                            # Vanished under us, so there is nothing to report or prune.
        broken = {"path": path, "query": None, "instance": None, "ageDays": None, "bytes": size}
        try:
            with open(path) as f:
                rec = json.load(f)
        except (OSError, ValueError):
            out.append(broken)
            continue
        if not isinstance(rec, dict) or rec.get("result") is None:
            out.append(broken)
            continue
        age = (time.time() - os.path.getmtime(path)) / 86400.0
        out.append({
            "path": path,
            "query": rec.get("query"),
            "instance": rec.get("instance"),
            "ageDays": age if age >= 0 else float("inf"),
            "bytes": size,
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
            except IsADirectoryError:
                print(f"  warning: {e['path']} is a directory, not a cache entry; remove it by hand")
            except OSError:
                pass
    return gone
