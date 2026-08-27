"""
Reads the sample config files and filters them.
The file format is documented in config/samples/README.txt and the CLAUDE.md beside it.
"""

# Import Block

## Standard Python imports
import itertools
import os
import re

## Kamui modules
from ..foundations import paths
from ..foundations.config import deepMerge, loadJson

# Classes and Functions

## Characters a sample name may use
NAME_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

## Every field a sample may carry. Documented in config/samples/README.txt
SAMPLE_FIELDS = {"name", "dataset", "dasInstance", "isMC", "era", "family", "content", "tags", "unitsPerJob", "lumiMask", "notes"}

class Sample(dict):
    """A dictionary with attribute access, just so sample.name reads better in f-strings."""

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k) from None

    def __repr__(self):
        return f"<Sample {self.get('name')}>"


def _axisPoints(axisName, entries):
    """Normalize one axis into a list of substitution dicts."""
    out = []
    for e in entries:
        if isinstance(e, dict):
            out.append(dict(e))
        else:
            out.append({axisName: str(e)})
    return out


def _expandGrid(grid, defaults):
    """Cartesian product of the axes -> list of sample dicts."""
    axisNames = list(grid.get("axes", {}).keys())
    points = [_axisPoints(a, grid["axes"][a]) for a in axisNames]
    skip = set(grid.get("skip", []))

    generated = set()
    samples = []
    for combo in itertools.product(*points) if points else [()]:
        subs = {}
        for part in combo:
            subs.update(part)
        name = grid["name"].format(**subs)
        generated.add(name)
        if name in skip:
            continue
        s = dict(defaults)
        s.update({k: v for k, v in grid.items() if k in SAMPLE_FIELDS and k not in ("name", "dataset")})
        s["name"] = name
        s["dataset"] = grid["dataset"].format(**subs)
        for k, v in subs.items():
            if k in SAMPLE_FIELDS:
                s[k] = v
        s.setdefault("notes", "")
        s["_axes"] = subs
        samples.append(s)

    stale = sorted(skip - generated)
    if stale:
        raise ValueError(f"grid '{grid.get('name')}' skips sample(s) it never generates: {stale}")
    return samples, generated


def _loadFamily(path):
    cfg = loadJson(path)
    defaults = cfg.get("defaults", {})
    defaults = dict(defaults)
    defaults.setdefault("family", cfg.get("family", os.path.basename(path)[:-5]))

    out = []
    generated = set()
    for grid in cfg.get("grids", []):
        expanded, names = _expandGrid(grid, defaults)
        generated |= names
        out.extend(expanded)
    for s in cfg.get("samples", []):
        merged = deepMerge(defaults, s)
        out.append(merged)

    overrides = cfg.get("overrides", {})
    preOverrideNames = {x["name"] for x in out if "name" in x}
    seen = set()
    final = []
    for s in out:
        if s["name"] in overrides:
            s = deepMerge(s, overrides[s["name"]])
        if not NAME_OK.fullmatch(s["name"]):
            raise ValueError(f"{path}: sample name {s['name']!r} has characters that break job lists, shell scripts and EOS paths; use letters, digits, dot, dash, underscore")
        if s["name"] in seen:
            raise ValueError(f"{path}: duplicate sample name '{s['name']}'")
        seen.add(s["name"])
        bad = set(s) - SAMPLE_FIELDS - {"_axes"}
        if bad:
            raise ValueError(f"{path}: sample '{s['name']}' has unknown field(s): {sorted(bad)}")
        if "dataset" not in s:
            raise ValueError(f"{path}: sample '{s['name']}' has no dataset")
        u = s.get("unitsPerJob")
        if u is not None and (isinstance(u, bool) or not isinstance(u, int) or u < 1):
            raise ValueError(f"{path}: sample '{s['name']}' has unitsPerJob {u!r}; it must be a positive integer")
        s.setdefault("dasInstance", "prod/global")
        s.setdefault("isMC", True)
        s.setdefault("content", "dvBase")
        s.setdefault("tags", [])
        final.append(Sample(s))

    stale = sorted(set(overrides) - seen - preOverrideNames)
    if stale:
        raise ValueError(f"{path}: overrides name sample(s) that do not exist: {stale}")
    return final


def loadCatalog(samplesDir=None):
    """Load every family file into one list of Sample."""
    samplesDir = samplesDir or paths.SAMPLES_DIR
    files = sorted(f for f in os.listdir(samplesDir) if f.endswith(".json"))
    catalog = []
    names = set()
    for f in files:
        for s in _loadFamily(os.path.join(samplesDir, f)):
            if s["name"] in names:
                raise ValueError(f"duplicate sample name across families: '{s['name']}'")
            names.add(s["name"])
            catalog.append(s)
    return catalog


def _resolve(value, allowed, what):
    """Return the catalog's own spelling of a family, era or tag, matched case-insensitively, and raise if it exists nowhere."""
    allowed = {a for a in allowed if a}
    if value in allowed:
        return value
    hit = sorted(a for a in allowed if a.lower() == value.lower())
    if len(hit) > 1:
        raise KeyError(f"{what} '{value}' is ambiguous; the catalog spells it {hit}. Use the exact spelling.")
    if hit:
        return hit[0]
    plural = "families" if what == "family" else what + "s"
    raise KeyError(f"unknown {what} '{value}'. Known {plural}: {', '.join(sorted(allowed))}")


def select(catalog, names=None, family=None, era=None, tag=None, pattern=None):
    """Filter a catalog. All given criteria must match."""
    import fnmatch

    out = catalog
    if names:
        wanted = set(names)
        out = [s for s in out if s["name"] in wanted]
        missing = wanted - {s["name"] for s in out}
        if missing:
            raise KeyError(f"unknown sample(s): {sorted(missing)}")
    if family:
        family = _resolve(family, {s.get("family") for s in catalog}, "family")
        out = [s for s in out if s.get("family") == family]
    if era:
        era = _resolve(era, {s.get("era") for s in catalog}, "era")
        out = [s for s in out if s.get("era") == era]
    if tag:
        tag = _resolve(tag, {t for s in catalog for t in s.get("tags", [])}, "tag")
        out = [s for s in out if tag in s.get("tags", [])]
    if pattern:
        out = [s for s in out if fnmatch.fnmatch(s["name"], pattern)]
    return out
