"""
Reads the sample config files and filters them. The file format is documented in config/samples/README.md.
"""

# Import Block

## Standard Python imports
import itertools
import fnmatch
import os
import re

## Kamui modules
from ..foundations import paths
from ..foundations.config import deepMerge, eraGroup, loadJson

# Classes and Functions

## Characters a sample name may use
NAME_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

## Every field a sample may carry. Documented in config/samples/README.md
SAMPLE_FIELDS = {"name", "dataset", "dasInstance", "isMC", "era", "family", "content", "tags", "unitsPerJob", "lumiMask"}

## Every key a family file may carry at its top level
FAMILY_FIELDS = {"family", "defaults", "samples", "grids", "overrides"}

## Every key a grid may carry: its templates and axes, plus any sample field it applies to every point
GRID_FIELDS = {"axes", "skip"} | SAMPLE_FIELDS

## Whether a central dataset tier holds MC, so a sample's isMC can be checked against its dataset
TIER_IS_MC = {"MINIAODSIM": True, "MINIAOD": False}

def _axisPoints(axisName, entries):
    """Normalize one axis into a list of substitution dicts."""
    out = []
    for e in entries:
        if isinstance(e, dict):
            out.append(dict(e))
        else:
            out.append({axisName: str(e)})
    return out


def _fill(where, template, subs):
    """A grid template with its placeholders filled in from one point of the axes."""
    try:
        return template.format(**subs)
    except KeyError as e:
        raise ValueError(f"{where} uses the placeholder {{{e.args[0]}}}, which no axis fills") from None


def _expandGrid(grid, defaults, path):
    """The Cartesian product of the axes, as a list of sample dicts."""
    if not isinstance(grid, dict):
        raise ValueError(f"{path}: every entry under 'grids' must be an object")
    where = f"{path}: grid '{grid.get('name')}'"
    bad = sorted(set(grid) - GRID_FIELDS)
    if bad:
        raise ValueError(f"{where} has unknown key(s) {bad}; valid keys are {sorted(GRID_FIELDS)}")
    for key in ("name", "dataset"):
        if not isinstance(grid.get(key), str):
            raise ValueError(f"{where} needs a '{key}' template")
    axes = grid.get("axes", {})
    if not isinstance(axes, dict) or not all(isinstance(v, list) and v for v in axes.values()):
        raise ValueError(f"{where} needs 'axes' to be an object of non-empty lists")
    axisNames = list(axes.keys())
    points = [_axisPoints(a, axes[a]) for a in axisNames]
    skip = set(grid.get("skip", []))

    generated = set()
    samples = []
    for combo in itertools.product(*points) if points else [()]:
        subs = {}
        for part in combo:
            subs.update(part)
        name = _fill(where, grid["name"], subs)
        generated.add(name)
        if name in skip:
            continue
        s = dict(defaults)
        s.update({k: v for k, v in grid.items() if k in SAMPLE_FIELDS and k not in ("name", "dataset")})
        s["name"] = name
        s["dataset"] = _fill(where, grid["dataset"], subs)
        for k, v in subs.items():
            if k in SAMPLE_FIELDS:
                s[k] = v
        samples.append(s)

    stale = sorted(skip - generated)
    if stale:
        raise ValueError(f"{where} skips sample(s) it never generates: {stale}")
    return samples


def _loadFamily(path):
    cfg = loadJson(path)
    if not isinstance(cfg, dict):
        raise ValueError(f"{path}: the top level must be an object")
    bad = sorted(set(cfg) - FAMILY_FIELDS)
    if bad:
        raise ValueError(f"{path}: unknown key(s) {bad}; valid keys are {sorted(FAMILY_FIELDS)}")
    defaults = cfg.get("defaults", {})
    grids = cfg.get("grids", [])
    samples = cfg.get("samples", [])
    overrides = cfg.get("overrides", {})
    if not isinstance(defaults, dict):
        raise ValueError(f"{path}: 'defaults' must be an object of sample fields")
    if not isinstance(grids, list):
        raise ValueError(f"{path}: 'grids' must be a list of grids")
    if not isinstance(samples, list) or not all(isinstance(s, dict) for s in samples):
        raise ValueError(f"{path}: 'samples' must be a list of sample objects")
    if not isinstance(overrides, dict) or not all(isinstance(o, dict) for o in overrides.values()):
        raise ValueError(f"{path}: 'overrides' must be an object of sample fields keyed by sample name")
    defaults = dict(defaults)
    defaults.setdefault("family", cfg.get("family", os.path.basename(path)[:-5]))

    out = []
    for grid in grids:
        out.extend(_expandGrid(grid, defaults, path))
    for j, s in enumerate(samples):
        if not isinstance(s.get("name"), str):
            raise ValueError(f"{path}: sample {j} under 'samples' has no name")
        merged = deepMerge(defaults, s)
        out.append(merged)
    if not out:
        raise ValueError(f"{path}: defines no samples; list them under 'samples' or generate them from 'grids'")

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
        bad = set(s) - SAMPLE_FIELDS
        if bad:
            raise ValueError(f"{path}: sample '{s['name']}' has unknown field(s): {sorted(bad)}")
        if not isinstance(s.get("dataset"), str):
            raise ValueError(f"{path}: sample '{s['name']}' has no dataset")
        if not isinstance(s.get("era"), str) or not s["era"]:
            raise ValueError(f"{path}: sample '{s['name']}' has no era; set 'era' on the sample, its grid or the file's defaults")
        ## isMC decides the global tag, the MC-only collections and whether a blind selection may run, so it is never guessed
        if "isMC" not in s:
            raise ValueError(f"{path}: sample '{s['name']}' has no isMC; set it to true for MC or false for data")
        if not isinstance(s["isMC"], bool):
            raise ValueError(f"{path}: sample '{s['name']}' has isMC {s['isMC']!r}; write true or false without quotes")
        tier = s["dataset"].rsplit("/", 1)[-1]
        if tier in TIER_IS_MC and TIER_IS_MC[tier] != s["isMC"]:
            raise ValueError(f"{path}: sample '{s['name']}' has isMC {str(s['isMC']).lower()}, but its dataset tier {tier} holds {'MC' if TIER_IS_MC[tier] else 'data'}")
        u = s.get("unitsPerJob")
        if u is not None and (isinstance(u, bool) or not isinstance(u, int) or u < 1):
            raise ValueError(f"{path}: sample '{s['name']}' has unitsPerJob {u!r}; it must be a positive integer")
        s.setdefault("dasInstance", "prod/global")
        s.setdefault("content", "dvBase")
        s.setdefault("tags", [])
        if not isinstance(s["tags"], list) or not all(isinstance(t, str) and t for t in s["tags"]):
            raise ValueError(f"{path}: sample '{s['name']}' has tags {s['tags']!r}; tags must be a list of names, such as [\"signal\"]")
        final.append(s)

    stale = sorted(set(overrides) - seen - preOverrideNames)
    if stale:
        raise ValueError(f"{path}: overrides name sample(s) that do not exist: {stale}")
    return final


def loadCatalog(samplesDir=None):
    """Load every family file into one list of samples."""
    samplesDir = samplesDir or paths.SAMPLES_DIR
    ## Walked recursively so families can be grouped into subdirectories; a sample means the same thing wherever its file sits.
    files = sorted(os.path.join(root, f) for root, _, names in os.walk(samplesDir) for f in names if f.endswith(".json"))
    catalog = []
    names = {}
    for path in files:
        rel = os.path.relpath(path, samplesDir)
        for s in _loadFamily(path):
            if s["name"] in names:
                raise ValueError(f"{rel}: sample name '{s['name']}' is already used in {names[s['name']]}")
            ## A family sits in its run's folder, so the folder a reader sees always matches the run Kamui uses
            if rel.split(os.sep)[0] != eraGroup(s["era"]):
                raise ValueError(f"Sample '{s['name']}' is a {eraGroup(s['era'])} sample ({s['era']}), so {rel} belongs under {eraGroup(s['era'])}/")
            names[s["name"]] = rel
            catalog.append(s)
    return catalog


def _resolve(value, allowed, what):
    """Return the catalog's own spelling of a family, era or tag, matched case-insensitively, and raise if it exists nowhere."""
    allowed = {a for a in allowed if a}
    if value in allowed:
        return value
    hit = sorted(a for a in allowed if a.lower() == value.lower())
    if len(hit) > 1:
        raise KeyError(f"Ambiguous {what} '{value}': the catalog spells it {hit}. Use the exact spelling.")
    if hit:
        return hit[0]
    plural = "families" if what == "family" else what + "s"
    raise KeyError(f"Unknown {what} '{value}'. Known {plural}: {', '.join(sorted(allowed))}")


def select(catalog, names=None, family=None, era=None, tag=None, pattern=None):
    """Filter a catalog. All given criteria must match."""

    out = catalog
    if names:
        wanted = set(names)
        out = [s for s in out if s["name"] in wanted]
        missing = wanted - {s["name"] for s in out}
        if missing:
            raise KeyError(f"Unknown sample(s): {sorted(missing)}")
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
