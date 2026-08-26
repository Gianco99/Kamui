"""
Loads the JSON config files.
"""

# Import Block

## Standard Python imports
import json
import os

# Function Block

def stripComments(obj):
    """Recursively drop dict keys beginning with '_'."""
    if isinstance(obj, dict):
        return {k: stripComments(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [stripComments(v) for v in obj]
    return obj

def deepMerge(base, over):
    """Merge `over` into `base` recursively. Lists and scalars are replaced."""
    out = dict(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deepMerge(out[k], v)
        else:
            out[k] = v
    return out

def loadJson(path):
    """Load one JSON file, with comment keys stripped. No include handling."""
    with open(path) as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: {e}") from None
    return stripComments(raw)

def _resolvePath(nameOrPath, searchDir):
    """Accept 'jets', 'jets.json' or an explicit path; return an existing path."""
    if os.path.sep in nameOrPath or nameOrPath.endswith(".json"):
        cand = nameOrPath if os.path.isabs(nameOrPath) else os.path.join(searchDir, nameOrPath)
        if os.path.exists(cand):
            return cand
        if os.path.exists(nameOrPath):
            return nameOrPath
    ## Search searchDir itself, then one level of subdirectories, so a name resolves without having to say which folder it lives in
    for d in [searchDir] + [os.path.join(searchDir, x) for x in sorted(os.listdir(searchDir)) if os.path.isdir(os.path.join(searchDir, x))]:
        cand = os.path.join(d, nameOrPath + ".json")
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"no config '{nameOrPath}' under {searchDir}")

def loadWithIncludes(nameOrPath, searchDir, _seen=None):
    """Load a config and flatten its "include" chain (depth-first, deep-merged)."""
    path = _resolvePath(nameOrPath, searchDir)
    _seen = _seen if _seen is not None else []
    real = os.path.realpath(path)
    if real in _seen:
        raise ValueError(f"circular include: {' -> '.join(_seen + [real])}")
    _seen = _seen + [real]

    cfg = loadJson(path)
    merged = {}
    for inc in cfg.pop("include", []):
        merged = deepMerge(merged, loadWithIncludes(inc, searchDir, _seen))
    merged = deepMerge(merged, cfg)
    return merged
