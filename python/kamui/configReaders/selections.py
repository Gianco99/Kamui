"""
Reads the selection configs that drive the ntupleSelection stage.
"""

# Import Block

## Standard Python imports
import math
import os

## Kamui modules
from ..foundations import paths
from ..foundations.config import RUNS, isNameList, loadWithIncludes, runDir
from ..configReaders.content import loadTriggerConfig
from .requirements import BOUNDS, resolveRequirements, resolveThreshold

## Every top-level key a selection config may carry
SELECTION_FIELDS = {"eras", "cuts", "blind"}

## Every key a cut of any type may carry. The keys each type adds are listed in CUT_RESOLVERS at the end of this file.
COMMON_CUT_FIELDS = {"name", "type", "doc", "invert"}

## Every key one alternative of an anyOf cut may carry
ALTERNATIVE_FIELDS = {"name", "doc", "eras", "cuts"}

## Every key one condition may carry
CONDITION_FIELDS = {"quantity"} | set(BOUNDS)

## Every key an inline quantity may carry
AGGREGATE_FIELDS = {"collection", "sum", "requirements"}

## Every key one pair requirement may carry. A pair requirement cuts on two objects at once, such as |eta_i - eta_j| < 1.6.
PAIR_FIELDS = {"variable", "absDiffMin", "absDiffMax"}

## The signal region: a selection keeping events with this many DVs of at least this many tracks has to be blind
SIGNAL_REGION = {"collection": "DV", "minDvs": 2, "minTracks": 5}


def listSelections(selectionDir=None):
    """Every selection config, by name."""
    selectionDir = selectionDir or paths.SELECTIONS_DIR
    if not os.path.isdir(selectionDir):
        return []
    return sorted(f[:-5] for f in os.listdir(selectionDir) if f.endswith(".json"))


def selectionFiles(selectionDir=None):
    """Every selection config as (run, folder, name), from one folder per run."""
    selectionDir = selectionDir or paths.SELECTIONS_DIR
    return [(r, os.path.join(selectionDir, r), n) for r in RUNS for n in listSelections(os.path.join(selectionDir, r))]


def selectionEras(name, selectionDir=None):
    """The eras a selection config declares, empty when it names none."""
    cfg = loadWithIncludes(name, selectionDir or paths.SELECTIONS_DIR)
    return list(cfg.get("eras") or [])


def runEras(run, selectionDir=None):
    """Every era the selections of one run declare, the eras a selection or definition that names none is checked for."""
    return sorted({e for r, folder, n in selectionFiles(selectionDir) if r == run for e in selectionEras(n, folder)})


def resolveSelection(name, selectionDir=None, era=None):
    """Flatten a selection config and resolve every era-dependent threshold to a single number. Names joined by commas stack: their cuts run in the order given, and the stack is blind when any part is."""
    ## An empty part, as a trailing comma leaves, names nothing and is dropped
    names = [part.strip() for part in name.split(",") if part.strip()]
    if not names:
        raise ValueError(f"Selection {name!r} names no selection config; give one name, or several joined by commas such as lepton,dv3x4")
    if len(names) > 1:
        parts = [resolveSelection(part, selectionDir, era) for part in names]
        return {"name": ",".join(names), "era": era, "blind": any(p["blind"] for p in parts), "cuts": [cut for p in parts for cut in p["cuts"]]}
    name = names[0]

    selectionDir = selectionDir or runDir(paths.SELECTIONS_DIR, era)
    cfg = loadWithIncludes(name, selectionDir)

    unknown = sorted(set(cfg) - SELECTION_FIELDS)
    if unknown:
        raise ValueError(f"Selection '{name}' has unknown key(s) {unknown}; valid keys are {sorted(SELECTION_FIELDS)}")
    if not isinstance(cfg.get("cuts"), list) or not cfg["cuts"]:
        raise ValueError(f"Selection '{name}' defines no cuts")

    eras = cfg.get("eras")
    if eras is not None and not isNameList(eras):
        raise ValueError(f"Selection '{name}': eras must be a list of era names")
    if eras and era is not None and era not in eras:
        raise ValueError(f"Selection '{name}' applies to eras {eras}, not '{era}'")

    cuts = [_resolveCut(name, cut, era, i) for i, cut in enumerate(cfg["cuts"])]

    blind = cfg.get("blind", False)
    if not isinstance(blind, bool):
        raise ValueError(f"Selection '{name}': blind must be true or false")
    if not blind and _keepsSignalRegion(cuts):
        raise ValueError(f"Selection '{name}' keeps events with {SIGNAL_REGION['minDvs']} or more DVs of {SIGNAL_REGION['minTracks']} or more tracks, the signal region, so it must say \"blind\": true")
    return {"name": name, "era": era, "blind": blind, "cuts": cuts}


def _keepsSignalRegion(cuts):
    """Whether a cut asks for enough DVs with enough tracks to reach into the signal region. Definitions are expanded by now, so a DV cut hidden in one is seen too."""
    for cut in cuts:
        if cut["type"] == "quantity":
            for cond in cut["conditions"]:
                q = cond["quantity"]
                if isinstance(q, dict) and "sum" not in q and _isSignalCount(q["collection"], q["requirements"], _fewestKept(cut, cond)):
                    return True
        elif cut.get("invert"):
            continue
        elif cut["type"] == "anyOf" and any(_keepsSignalRegion(option["cuts"]) for option in cut["anyOf"]):
            return True
        elif cut["type"] == "object" and _isSignalCount(cut["collection"], cut["requirements"], cut["min"]):
            return True
    return False


def _fewestKept(cut, cond):
    """The fewest objects that cond counts in any event the cut keeps. An inverted cut with one condition keeps the counts outside it, which all lie above its upper end when it has no lower end."""
    if not cut.get("invert"):
        return _lowest(cond)
    if len(cut["conditions"]) == 1 and _lowest(cond) <= 0 and _highest(cond) < math.inf:
        return _highest(cond) + 1
    return -math.inf


def _isSignalCount(collection, reqs, fewest):
    """Whether at least `fewest` objects of a collection passing reqs means signal-region DVs."""
    return collection == SIGNAL_REGION["collection"] and fewest >= SIGNAL_REGION["minDvs"] and _fewestTracks(reqs) >= SIGNAL_REGION["minTracks"]


def _fewestTracks(reqs):
    """The fewest tracks a DV passing these resolved requirements can have."""
    fewest = -math.inf
    for req in reqs:
        if "anyOf" in req:
            fewest = max(fewest, min(_fewestTracks(group) for group in req["anyOf"]))
        elif req["variable"] == "nTracks":
            fewest = max(fewest, _lowest(req))
    return fewest


## Counts and track numbers are never negative, so an absolute bound on one reads as the plain bound
def _lowest(bounds):
    """The smallest whole number a set of bounds lets through, from its lower ends."""
    lowest = -math.inf
    for key in ("min", "absMin"):
        if key in bounds:
            lowest = max(lowest, math.ceil(bounds[key]))
    for key in ("above", "absAbove"):
        if key in bounds:
            lowest = max(lowest, math.floor(bounds[key]) + 1)
    return lowest


def _highest(bounds):
    """The largest whole number a set of bounds lets through, from its upper ends."""
    highest = math.inf
    for key in ("max", "absMax"):
        if key in bounds:
            highest = min(highest, math.floor(bounds[key]))
    for key in ("below", "absBelow"):
        if key in bounds:
            highest = min(highest, math.ceil(bounds[key]) - 1)
    return highest


def _resolveCut(name, cut, era, i):
    """One cut, with every era-dependent threshold, trigger list and flag list resolved."""
    if not isinstance(cut, dict):
        raise ValueError(f"Selection '{name}': cut {i} must be an object")
    if "name" not in cut:
        raise ValueError(f"Selection '{name}': cut {i} has no 'name'")
    kind = cut.get("type")
    if kind not in CUT_RESOLVERS:
        raise ValueError(f"Selection '{name}': cut '{cut['name']}' has type '{kind}'; valid types are {sorted(CUT_TYPES)}")

    where = f"Selection '{name}': cut '{cut['name']}'"
    fields, resolver = CUT_RESOLVERS[kind]
    bad = sorted(set(cut) - COMMON_CUT_FIELDS - fields)
    if bad:
        hint = ". 'eras' belongs on an alternative of an anyOf cut" if "eras" in bad else ""
        raise ValueError(f"{where} has unknown key(s) {bad}; a '{kind}' cut takes {sorted(COMMON_CUT_FIELDS | fields)}{hint}")
    if not isinstance(cut.get("invert", False), bool):
        raise ValueError(f"{where}: invert must be true or false")

    out = {"name": cut["name"], "type": kind, "doc": cut.get("doc", "")}
    if cut.get("invert"):
        out["invert"] = True
    out.update(resolver(name, where, cut, era))
    return out


def _forEra(where, what, value, era):
    """A value written once, or the entry for this era of a value keyed by era."""
    if not isinstance(value, dict):
        return value
    if era is None:
        raise ValueError(f"{where} has per-era {what} but no era was given")
    if era not in value:
        raise ValueError(f"{where} defines no {what} for era '{era}'; it defines {sorted(value)}")
    return value[era]


def _resolveAnyOf(name, where, cut, era):
    """ORed alternatives of ordinary cuts. An alternative outside this era is dropped here, so it cannot fail on a trigger path the era never had."""
    options = cut.get("anyOf")
    if not isinstance(options, list) or not options:
        raise ValueError(f"{where} of type 'anyOf' needs a non-empty 'anyOf' list")
    resolvedOptions = []
    for j, option in enumerate(options):
        if not isinstance(option, dict) or "cuts" not in option:
            raise ValueError(f"{where} alternative {j} must be an object with 'cuts'")
        label = f"{where} alternative '{option.get('name', j)}'"
        bad = sorted(set(option) - ALTERNATIVE_FIELDS)
        if bad:
            raise ValueError(f"{label} has unknown key(s) {bad}; valid keys are {sorted(ALTERNATIVE_FIELDS)}")
        if not isinstance(option["cuts"], list) or not option["cuts"]:
            raise ValueError(f"{label} needs a non-empty 'cuts' list")
        if "eras" in option and not isNameList(option["eras"]):
            raise ValueError(f"{label}: eras must be a list of era names")
        if era is not None and option.get("eras") and era not in option["eras"]:
            continue
        resolvedOptions.append({
            "name": option.get("name", f"alternative {j}"),
            "doc": option.get("doc", ""),
            "cuts": [_resolveCut(name, sub, era, f"{cut['name']}[{j}].{k}") for k, sub in enumerate(option["cuts"])],
        })
    if era is not None and not resolvedOptions:
        raise ValueError(f"{where} has no alternative that applies to era '{era}'")
    return {"anyOf": resolvedOptions}


def _resolveConditions(name, where, cut, era):
    """Every condition on an event quantity must hold. A single condition may sit on the cut itself, as a quantity and its bounds."""
    if "conditions" in cut:
        inline = sorted(set(cut) & CONDITION_FIELDS)
        if inline:
            raise ValueError(f"{where} has 'conditions' and also {inline}; put those inside a condition")
        raw = cut["conditions"]
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"{where} needs 'conditions' to be a non-empty list")
    elif "quantity" in cut:
        raw = [{k: cut[k] for k in CONDITION_FIELDS if k in cut}]
    else:
        raise ValueError(f"{where} of type 'quantity' needs 'conditions' or a 'quantity'")
    conditions = []
    for cond in raw:
        if not isinstance(cond, dict):
            raise ValueError(f"{where} has a condition that is not an object")
        bad = sorted(set(cond) - CONDITION_FIELDS)
        if bad:
            raise ValueError(f"{where} has a condition with unknown key(s) {bad}; valid keys are {sorted(CONDITION_FIELDS)}")
        resolved = {"quantity": _resolveQuantity(where, cond.get("quantity"), era)}
        for bound in BOUNDS:
            if bound in cond:
                resolved[bound] = resolveThreshold(where, bound, cond[bound], era)
        if len(resolved) == 1:
            raise ValueError(f"{where} has a condition with no bound")
        conditions.append(resolved)
    return {"conditions": conditions}


def _resolveFlags(name, where, cut, era):
    """Every named flag must be true. Which flags apply depends on the era."""
    flags = _forEra(where, "flags", cut.get("flags"), era)
    if not isNameList(flags):
        raise ValueError(f"{where} of type 'flags' needs a non-empty 'flags' list of branch names")
    return {"flags": list(flags)}


def _resolveTrigger(name, where, cut, era):
    """Any of the paths must have fired. Which paths existed depends on the year, so a trigger list may be keyed by era."""
    if "triggers" not in cut:
        raise ValueError(f"{where} of type 'trigger' needs 'triggers'")
    triggers = _forEra(where, "triggers", cut["triggers"], era)
    if isinstance(triggers, str):
        ## The path list is expanded here so the resolved selection is self-contained and a worker never reads config/triggers/.
        trig = loadTriggerConfig(triggers, era)
        if trig["mode"] != "any":
            raise ValueError(f"{where} names trigger config '{triggers}', whose mode is '{trig['mode']}'; a trigger cut keeps an event when any of its paths fired, so it reads only configs with mode 'any'")
        return {"triggers": triggers, "hltPaths": trig["paths"]}
    if not isNameList(triggers):
        raise ValueError(f"{where} has 'triggers' that is neither a trigger config name nor a non-empty list of path patterns")
    return {"triggers": triggers, "hltPaths": list(triggers)}


def _resolveQuantity(where, q, era):
    """An event branch by name, or an inline count or sum over the objects of a collection passing requirements."""
    if isinstance(q, str):
        return q
    if not isinstance(q, dict):
        raise ValueError(f"{where} has a quantity that is neither a branch name nor an object")
    bad = sorted(set(q) - AGGREGATE_FIELDS)
    if bad:
        raise ValueError(f"{where} has a quantity with unknown key(s) {bad}; valid keys are {sorted(AGGREGATE_FIELDS)}")
    if "collection" not in q:
        raise ValueError(f"{where} has a quantity with no 'collection'")
    out = {"collection": q["collection"], "requirements": resolveRequirements(where, q["requirements"], era) if q.get("requirements") else []}
    if "sum" in q:
        out["sum"] = q["sum"]
    return out


def _count(where, key, value, least):
    """An object count, which must be a whole number of at least `least`."""
    if isinstance(value, bool) or not isinstance(value, int) or value < least:
        raise ValueError(f"{where} has {key} {value!r}; an object count must be a whole number of at least {least}")
    return value


def _resolveObject(name, where, cut, era):
    """How many objects of one collection must satisfy every requirement."""
    if not isinstance(cut.get("collection"), str):
        raise ValueError(f"{where} of type 'object' has no 'collection'")
    reqs = resolveRequirements(where, cut.get("requirements"), era)

    ## An upper end makes the cut a count condition, the form the engine bounds from above, so "max": 0 vetoes every event holding such an object
    if "max" in cut:
        if "orderedMinPt" in cut or "pairRequirements" in cut:
            raise ValueError(f"{where} has 'max' together with 'orderedMinPt' or 'pairRequirements'; put the upper end on the count in a cut of its own")
        cond = {"quantity": {"collection": cut["collection"], "requirements": reqs}}
        if "min" in cut:
            cond["min"] = float(_count(where, "min", cut["min"], 1))
        cond["max"] = float(_count(where, "max", cut["max"], 0))
        if cond.get("min", 0) > cond["max"]:
            raise ValueError(f"{where} has min {cut['min']} above max {cut['max']}, so no event can pass")
        return {"type": "quantity", "conditions": [cond]}

    ## A pT ladder says how many objects there must be, so it supplies the count when none is given.
    ladder = cut.get("orderedMinPt")
    if ladder is not None:
        if not isinstance(ladder, list) or not ladder:
            raise ValueError(f"{where} has an 'orderedMinPt' that is not a non-empty list")
        ladder = [resolveThreshold(where, "orderedMinPt", v, era) for v in ladder]
        if ladder != sorted(ladder, reverse=True):
            raise ValueError(f"{where} has 'orderedMinPt' {ladder}, which must be in descending order because it is matched against pT-ordered objects")

    out = {"collection": cut["collection"], "min": _count(where, "min", cut.get("min", len(ladder) if ladder else 1), 1), "requirements": reqs}
    if ladder:
        out["orderedMinPt"] = ladder

    pairList = cut.get("pairRequirements", [])
    if not isinstance(pairList, list) or not all(isinstance(pair, dict) for pair in pairList):
        raise ValueError(f"{where} has 'pairRequirements' that is not a list of objects")
    pairs = []
    for pair in pairList:
        bad = sorted(set(pair) - PAIR_FIELDS)
        if bad:
            raise ValueError(f"{where} has a pair requirement with unknown key(s) {bad}; valid keys are {sorted(PAIR_FIELDS)}")
        if "variable" not in pair:
            raise ValueError(f"{where} has a pair requirement with no 'variable'")
        resolved = {"variable": pair["variable"]}
        for bound in ("absDiffMin", "absDiffMax"):
            if bound in pair:
                resolved[bound] = resolveThreshold(where, bound, pair[bound], era)
        if len(resolved) == 1:
            raise ValueError(f"{where} pair requirement on '{pair['variable']}' has no bound")
        pairs.append(resolved)
    if pairs:
        if out["min"] < 2:
            raise ValueError(f"{where} has a pair requirement but asks for fewer than two objects")
        out["pairRequirements"] = pairs
    return out


## Each cut type: the keys it may carry besides COMMON_CUT_FIELDS, and the function that resolves it
CUT_RESOLVERS = {
    "trigger":  ({"triggers"}, _resolveTrigger),
    "flags":    ({"flags"}, _resolveFlags),
    "quantity": ({"conditions"} | CONDITION_FIELDS, _resolveConditions),
    "object":   ({"collection", "requirements", "min", "max", "orderedMinPt", "pairRequirements"}, _resolveObject),
    "anyOf":    ({"anyOf"}, _resolveAnyOf),
}

## Cut types the engine knows how to apply
CUT_TYPES = set(CUT_RESOLVERS)
