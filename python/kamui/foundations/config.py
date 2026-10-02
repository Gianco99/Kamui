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

## Each config kind that differs by run keeps one folder per run, and an era reads only from its own run's folder
RUN2_ERAS = {"2016", "2016APV", "2017", "2018"}
RUNS = ("run2", "run3")


def eraGroup(era):
    """run2 or run3, the run whose config folders an era reads from."""
    return "run2" if era in RUN2_ERAS else "run3"


def runDir(kindDir, era):
    """The folder of a config kind that an era reads from, so a Run 3 job can never pick up a Run 2 file. Without an era, the whole kind is searched."""
    return os.path.join(kindDir, eraGroup(era)) if era else kindDir


def _resolvePath(nameOrPath, searchDir):
    """Accept 'jets', 'jets.json' or an explicit path; return an existing path. searchDir may be one directory or an ordered list."""
    dirs = [searchDir] if isinstance(searchDir, str) else list(searchDir)
    if os.path.sep in nameOrPath or nameOrPath.endswith(".json"):
        for d in dirs:
            cand = nameOrPath if os.path.isabs(nameOrPath) else os.path.join(d, nameOrPath)
            if os.path.exists(cand):
                return cand
    for base in dirs:
        if not os.path.isdir(base):
            continue
        ## A name found in two folders, such as run2/ and run3/, is an error, so a lookup never quietly takes the wrong one
        found = [c for c in (os.path.join(d, nameOrPath + ".json") for d in [base] + [os.path.join(base, x) for x in sorted(os.listdir(base)) if os.path.isdir(os.path.join(base, x))]) if os.path.exists(c)]
        if len(found) > 1:
            raise ValueError(f"Config '{nameOrPath}' matches {', '.join(found)}; name it with its folder, e.g. '{os.path.relpath(os.path.dirname(found[0]), base)}/{nameOrPath}'")
        if found:
            return found[0]
    raise FileNotFoundError(f"No config '{nameOrPath}' under {', '.join(dirs)}")

def loadWithIncludes(nameOrPath, searchDir, _seen=None):
    """Load a config and flatten its "include" chain (depth-first, deep-merged)."""
    path = _resolvePath(nameOrPath, searchDir)
    _seen = _seen if _seen is not None else []
    real = os.path.realpath(path)
    if real in _seen:
        raise ValueError(f"Circular include: {' -> '.join(_seen + [real])}")
    _seen = _seen + [real]

    cfg = loadJson(path)
    merged = {}
    for inc in cfg.pop("include", []):
        merged = deepMerge(merged, loadWithIncludes(inc, searchDir, _seen))
    merged = deepMerge(merged, cfg)
    return merged
