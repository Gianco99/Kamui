"""
Reads the selection configs that drive the ntupleSelection stage.
"""

# Import Block

## Standard Python imports
import os

## Kamui modules
from ..foundations import paths
from ..foundations.config import loadWithIncludes
from ..configReaders.content import loadTriggerPaths
from .requirements import BOUNDS, resolveRequirements, resolveThreshold

## Every top-level key a selection config may carry
SELECTION_FIELDS = {"eras", "cuts"}

## Every key a cut may carry
CUT_FIELDS = {"name", "type", "doc", "invert", "eras", "triggers", "flags", "quantity", "conditions", "collection", "requirements", "orderedMinPt", "pairRequirements", "anyOf"} | set(BOUNDS)

## Every key one condition may carry
CONDITION_FIELDS = {"quantity"} | set(BOUNDS)

## Every key an inline quantity may carry
AGGREGATE_FIELDS = {"collection", "sum", "requirements"}

## Every key one pair requirement may carry. A pair requirement cuts on two objects at once, such as |eta_i - eta_j| < 1.6.
PAIR_FIELDS = {"variable", "absDiffMin", "absDiffMax"}

## Cut kinds the engine knows how to apply
CUT_TYPES = {"trigger", "flags", "quantity", "object", "anyOf"}


def listSelections(selectionDir=None):
    """Every selection config, by name."""
    selectionDir = selectionDir or paths.SELECTIONS_DIR
    if not os.path.isdir(selectionDir):
        return []
    return sorted(f[:-5] for f in os.listdir(selectionDir) if f.endswith(".json"))


def selectionEras(name, selectionDir=None):
    """The eras a selection config declares, empty when it names none."""
    cfg = loadWithIncludes(name, selectionDir or paths.SELECTIONS_DIR)
    return list(cfg.get("eras") or [])


def resolveSelection(name, selectionDir=None, era=None):
    """Flatten a selection config and resolve every era-dependent threshold to a single number."""
    selectionDir = selectionDir or paths.SELECTIONS_DIR
    cfg = loadWithIncludes(name, selectionDir)

    unknown = sorted(set(cfg) - SELECTION_FIELDS)
    if unknown:
        raise ValueError(f"Selection '{name}' has unknown key(s) {unknown}; valid keys are {sorted(SELECTION_FIELDS)}")
    if not cfg.get("cuts"):
        raise ValueError(f"Selection '{name}' defines no cuts")

    eras = cfg.get("eras")
    if eras and era is not None and era not in eras:
        raise ValueError(f"Selection '{name}' applies to eras {eras}, not '{era}'")

    cuts = [_resolveCut(name, cut, era, i) for i, cut in enumerate(cfg["cuts"])]

    return {"name": name, "era": era, "cuts": cuts}


def _resolveCut(name, cut, era, i):
    """One cut, with every era-dependent threshold, trigger list and flag list resolved."""
    if not isinstance(cut, dict):
        raise ValueError(f"Selection '{name}': cut {i} must be an object")
    bad = sorted(set(cut) - CUT_FIELDS)
    if bad:
        raise ValueError(f"Selection '{name}': cut '{cut.get('name', i)}' has unknown key(s) {bad}; valid keys are {sorted(CUT_FIELDS)}")
    if "name" not in cut:
        raise ValueError(f"Selection '{name}': cut {i} has no 'name'")
    kind = cut.get("type")
    if kind not in CUT_TYPES:
        raise ValueError(f"Selection '{name}': cut '{cut['name']}' has type '{kind}'; valid types are {sorted(CUT_TYPES)}")

    where = f"Selection '{name}': cut '{cut['name']}'"
    out = {"name": cut["name"], "type": kind, "doc": cut.get("doc", "")}
    if cut.get("invert"):
        out["invert"] = True

    if kind == "anyOf":
        ## ORed alternatives of ordinary cuts. An alternative outside this era is dropped here, so it cannot fail on a trigger path the era never had.
        options = cut.get("anyOf")
        if not options:
            raise ValueError(f"{where} of type 'anyOf' needs a non-empty 'anyOf' list")
        resolvedOptions = []
        for j, option in enumerate(options):
            if not isinstance(option, dict) or "cuts" not in option:
                raise ValueError(f"{where} alternative {j} must be an object with 'cuts'")
            if era is not None and option.get("eras") and era not in option["eras"]:
                continue
            resolvedOptions.append({
                "name": option.get("name", f"alternative {j}"),
                "doc": option.get("doc", ""),
                "cuts": [_resolveCut(name, sub, era, f"{cut['name']}[{j}].{k}") for k, sub in enumerate(option["cuts"])],
            })
        if era is not None and not resolvedOptions:
            raise ValueError(f"{where} has no alternative that applies to era '{era}'")
        out["anyOf"] = resolvedOptions
        return out

    if kind == "quantity":
        raw = cut.get("conditions") or [{k: cut[k] for k in CONDITION_FIELDS if k in cut}]
        conditions = []
        for cond in raw:
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
        out["conditions"] = conditions

    if kind == "object":
        out.update(_resolveObject(where, cut, era))

    if kind == "flags":
        ## Every named flag must be true. Which flags apply depends on the era.
        flags = cut.get("flags")
        if isinstance(flags, dict):
            if era is None:
                raise ValueError(f"{where} has per-era flags but no era was given")
            if era not in flags:
                raise ValueError(f"{where} defines no flags for era '{era}'; it defines {sorted(flags)}")
            flags = flags[era]
        if not flags:
            raise ValueError(f"{where} of type 'flags' needs a non-empty 'flags' list")
        out["flags"] = list(flags)

    if kind == "trigger":
        if "triggers" not in cut:
            raise ValueError(f"{where} of type 'trigger' needs 'triggers'")
        triggers = cut["triggers"]
        ## Which paths existed depends on the year, so a trigger list may be keyed by era
        if isinstance(triggers, dict):
            if era is None:
                raise ValueError(f"{where} has per-era triggers but no era was given")
            if era not in triggers:
                raise ValueError(f"{where} defines no triggers for era '{era}'; it defines {sorted(triggers)}")
            triggers = triggers[era]
        out["triggers"] = triggers
        ## The path list is expanded here so the resolved selection is self-contained and a worker never reads config/triggers/.
        out["hltPaths"] = loadTriggerPaths(triggers) if isinstance(triggers, str) else list(triggers)

    return out


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


def _resolveObject(where, cut, era):
    """How many objects of one collection must satisfy every requirement."""
    if "collection" not in cut:
        raise ValueError(f"{where} of type 'object' has no 'collection'")
    reqs = resolveRequirements(where, cut.get("requirements"), era)

    ## A pT ladder says how many objects there must be, so it supplies the count when none is given.
    ladder = cut.get("orderedMinPt")
    if ladder is not None:
        if not isinstance(ladder, list) or not ladder:
            raise ValueError(f"{where} has an 'orderedMinPt' that is not a non-empty list")
        ladder = [resolveThreshold(where, "orderedMinPt", v, era) for v in ladder]
        if ladder != sorted(ladder, reverse=True):
            raise ValueError(f"{where} has 'orderedMinPt' {ladder}, which must be in descending order because it is matched against pT-ordered objects")

    out = {"collection": cut["collection"], "min": int(cut.get("min", len(ladder) if ladder else 1)), "requirements": reqs}
    if ladder:
        out["orderedMinPt"] = ladder

    pairs = []
    for pair in cut.get("pairRequirements", []):
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
