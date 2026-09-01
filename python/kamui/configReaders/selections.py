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
from ..select.quantities import QUANTITIES

## Every top-level key a selection config may carry
SELECTION_FIELDS = {"eras", "cuts"}

## Every key a cut may carry
CUT_FIELDS = {"name", "type", "triggers", "quantity", "min", "max", "conditions", "flags", "collection", "requirements", "anyOf", "doc", "invert", "eras", "cuts"}

## Every key one condition of a multi-part veto may carry
CONDITION_FIELDS = {"quantity", "min", "max"}

## Every key one per-object requirement may carry
REQUIREMENT_FIELDS = {"variable", "min", "max", "absMin", "absMax", "anyOf"}

## Every key one pair requirement may carry. A pair requirement is about two objects at once,
## which no per-object requirement can express: |eta_i - eta_j| < 1.6 is the case that needs it.
PAIR_FIELDS = {"variable", "absDiffMin", "absDiffMax"}

## Every key one leg of an object cut may carry
LEG_FIELDS = {"collection", "min", "requirements", "triggers", "doc", "pairRequirements", "orderedMinPt"}

## Cut kinds the engine knows how to apply
CUT_TYPES = {"trigger", "veto", "quantity", "flags", "object", "anyOf"}


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
        raise ValueError(f"selection '{name}' has unknown key(s) {unknown}; valid keys are {sorted(SELECTION_FIELDS)}")
    if not cfg.get("cuts"):
        raise ValueError(f"selection '{name}' defines no cuts")

    eras = cfg.get("eras")
    if eras and era is not None and era not in eras:
        raise ValueError(f"selection '{name}' applies to eras {eras}, not '{era}'")

    cuts = [_resolveCut(name, cut, era, i) for i, cut in enumerate(cfg["cuts"])]

    return {"name": name, "era": era, "cuts": cuts}


def _resolveCut(name, cut, era, i):
    """One cut, with every era-dependent threshold, trigger list and flag list resolved."""
    if not isinstance(cut, dict):
        raise ValueError(f"selection '{name}': cut {i} must be an object")
    bad = sorted(set(cut) - CUT_FIELDS)
    if bad:
        raise ValueError(f"selection '{name}': cut '{cut.get('name', i)}' has unknown key(s) {bad}; valid keys are {sorted(CUT_FIELDS)}")
    if "name" not in cut:
        raise ValueError(f"selection '{name}': cut {i} has no 'name'")
    kind = cut.get("type")
    if kind not in CUT_TYPES:
        raise ValueError(f"selection '{name}': cut '{cut['name']}' has type '{kind}'; valid types are {sorted(CUT_TYPES)}")

    out = {"name": cut["name"], "type": kind, "doc": cut.get("doc", "")}
    if cut.get("invert"):
        out["invert"] = True

    if kind == "anyOf":
        ## Alternatives, ORed. Each names its own cuts, which are ordinary cuts and are
        ## resolved the same way. An alternative that does not apply to this era is dropped
        ## here rather than left to fail silently on a missing trigger path.
        options = cut.get("anyOf")
        if not options:
            raise ValueError(f"selection '{name}': cut '{cut['name']}' of type 'anyOf' needs a non-empty 'anyOf' list")
        resolvedOptions = []
        for j, option in enumerate(options):
            if not isinstance(option, dict) or "cuts" not in option:
                raise ValueError(f"selection '{name}': cut '{cut['name']}' alternative {j} must be an object with 'cuts'")
            if era is not None and option.get("eras") and era not in option["eras"]:
                continue
            resolvedOptions.append({
                "name": option.get("name", f"alternative {j}"),
                "doc": option.get("doc", ""),
                "cuts": [_resolveCut(name, sub, era, f"{cut['name']}[{j}].{k}") for k, sub in enumerate(option["cuts"])],
            })
        if era is not None and not resolvedOptions:
            raise ValueError(f"selection '{name}': cut '{cut['name']}' has no alternative that applies to era '{era}'")
        out["anyOf"] = resolvedOptions
        return out

    if kind in ("quantity", "veto"):
        ## A veto may name several conditions, all of which must hold before the event is dropped
        raw = cut.get("conditions") or [{k: cut[k] for k in ("quantity", "min", "max") if k in cut}]
        conditions = []
        for cond in raw:
            bad = sorted(set(cond) - CONDITION_FIELDS)
            if bad:
                raise ValueError(f"selection '{name}': cut '{cut['name']}' has a condition with unknown key(s) {bad}")
            q = cond.get("quantity")
            if q not in QUANTITIES:
                raise ValueError(f"selection '{name}': cut '{cut['name']}' names quantity '{q}'; known quantities are {', '.join(sorted(QUANTITIES))}")
            resolved = {"quantity": q}
            for bound in ("min", "max"):
                if bound in cond:
                    resolved[bound] = _resolveThreshold(name, cut["name"], bound, cond[bound], era)
            if "min" not in resolved and "max" not in resolved:
                raise ValueError(f"selection '{name}': cut '{cut['name']}' condition on '{q}' needs a 'min' or a 'max'")
            conditions.append(resolved)
        out["conditions"] = conditions

    if kind == "object":
        ## An object cut is one or more legs. The event passes if any leg is satisfied,
        ## which is how a channel that accepts either a muon or an electron is written.
        legs = cut.get("anyOf") or [{k: cut[k] for k in ("collection", "min", "requirements") if k in cut}]
        out["legs"] = [_resolveLeg(name, cut["name"], leg, era) for leg in legs]

    if kind == "flags":
        ## Every named flag must be true. Which flags apply depends on the era.
        flags = cut.get("flags")
        if isinstance(flags, dict):
            if era is None:
                raise ValueError(f"selection '{name}': cut '{cut['name']}' has per-era flags but no era was given")
            if era not in flags:
                raise ValueError(f"selection '{name}': cut '{cut['name']}' defines no flags for era '{era}'; it defines {sorted(flags)}")
            flags = flags[era]
        if not flags:
            raise ValueError(f"selection '{name}': cut '{cut['name']}' of type 'flags' needs a non-empty 'flags' list")
        out["flags"] = list(flags)

    if kind in ("trigger", "veto"):
        if "triggers" not in cut:
            raise ValueError(f"selection '{name}': cut '{cut['name']}' of type '{kind}' needs 'triggers'")
        triggers = cut["triggers"]
        ## Which paths existed depends on the year, so a trigger list may be keyed by era
        if isinstance(triggers, dict):
            if era is None:
                raise ValueError(f"selection '{name}': cut '{cut['name']}' has per-era triggers but no era was given")
            if era not in triggers:
                raise ValueError(f"selection '{name}': cut '{cut['name']}' defines no triggers for era '{era}'; it defines {sorted(triggers)}")
            triggers = triggers[era]
        out["triggers"] = triggers
        ## Expand a trigger config name into its path list here, so the resolved selection
        ## is self-contained and a worker never has to read config/triggers/.
        out["hltPaths"] = loadTriggerPaths(triggers) if isinstance(triggers, str) else list(triggers)

    return out


def _resolveRequirement(selName, cutName, req, era):
    """One per-object requirement, or an 'anyOf' of requirement groups ORed per object."""
    bad = sorted(set(req) - REQUIREMENT_FIELDS)
    if bad:
        raise ValueError(f"selection '{selName}': cut '{cutName}' has a requirement with unknown key(s) {bad}; valid keys are {sorted(REQUIREMENT_FIELDS)}")

    if "anyOf" in req:
        ## Regions of one collection: an object satisfies any one group. This is what lets a
        ## bound depend on where the object is without duplicating the whole leg.
        if len(req) != 1:
            raise ValueError(f"selection '{selName}': cut '{cutName}' has a requirement mixing 'anyOf' with {sorted(set(req) - {'anyOf'})}")
        groups = req["anyOf"]
        if not isinstance(groups, list) or len(groups) < 2:
            raise ValueError(f"selection '{selName}': cut '{cutName}' has a requirement 'anyOf' that is not a list of at least two groups")
        for g in groups:
            if not isinstance(g, list) or not g:
                raise ValueError(f"selection '{selName}': cut '{cutName}' has an 'anyOf' group that is not a non-empty list")
        return {"anyOf": [[_resolveRequirement(selName, cutName, r, era) for r in g] for g in groups]}

    if "variable" not in req:
        raise ValueError(f"selection '{selName}': cut '{cutName}' has a requirement with no 'variable'")
    resolved = {"variable": req["variable"]}
    for bound in ("min", "max", "absMin", "absMax"):
        if bound in req:
            resolved[bound] = _resolveThreshold(selName, cutName, bound, req[bound], era)
    if len(resolved) == 1:
        raise ValueError(f"selection '{selName}': cut '{cutName}' requirement on '{req['variable']}' has no bound")
    return resolved


def _resolveLeg(selName, cutName, leg, era):
    """One leg of an object cut: how many objects of a collection must satisfy every requirement."""
    bad = sorted(set(leg) - LEG_FIELDS)
    if bad:
        raise ValueError(f"selection '{selName}': cut '{cutName}' has a leg with unknown key(s) {bad}; valid keys are {sorted(LEG_FIELDS)}")
    if "collection" not in leg:
        raise ValueError(f"selection '{selName}': cut '{cutName}' has a leg with no 'collection'")
    if not leg.get("requirements"):
        raise ValueError(f"selection '{selName}': cut '{cutName}' leg on '{leg['collection']}' has no requirements")

    reqs = [_resolveRequirement(selName, cutName, req, era) for req in leg["requirements"]]

    ## A pT ladder says how many objects there must be, so it supplies the count when none is given.
    ladder = leg.get("orderedMinPt")
    if ladder is not None:
        if not isinstance(ladder, list) or not ladder:
            raise ValueError(f"selection '{selName}': cut '{cutName}' has an 'orderedMinPt' that is not a non-empty list")
        ladder = [_resolveThreshold(selName, cutName, "orderedMinPt", v, era) for v in ladder]
        if ladder != sorted(ladder, reverse=True):
            raise ValueError(f"selection '{selName}': cut '{cutName}' has 'orderedMinPt' {ladder}, which must be in descending order because it is matched against pT-ordered objects")

    out = {"collection": leg["collection"], "min": int(leg.get("min", len(ladder) if ladder else 1)),
           "requirements": reqs, "doc": leg.get("doc", "")}
    if ladder:
        out["orderedMinPt"] = ladder

    pairs = []
    for pair in leg.get("pairRequirements", []):
        bad = sorted(set(pair) - PAIR_FIELDS)
        if bad:
            raise ValueError(f"selection '{selName}': cut '{cutName}' has a pair requirement with unknown key(s) {bad}; valid keys are {sorted(PAIR_FIELDS)}")
        if "variable" not in pair:
            raise ValueError(f"selection '{selName}': cut '{cutName}' has a pair requirement with no 'variable'")
        resolved = {"variable": pair["variable"]}
        for bound in ("absDiffMin", "absDiffMax"):
            if bound in pair:
                resolved[bound] = _resolveThreshold(selName, cutName, bound, pair[bound], era)
        if len(resolved) == 1:
            raise ValueError(f"selection '{selName}': cut '{cutName}' pair requirement on '{pair['variable']}' has no bound")
        pairs.append(resolved)
    if pairs:
        if out["min"] < 2:
            raise ValueError(f"selection '{selName}': cut '{cutName}' has a pair requirement but asks for fewer than two objects")
        out["pairRequirements"] = pairs

    ## A leg may be tied to the trigger it belongs to, so an offline plateau only counts
    ## when the path it emulates actually fired.
    if "triggers" in leg:
        triggers = leg["triggers"]
        if isinstance(triggers, dict):
            if era is None:
                raise ValueError(f"selection '{selName}': cut '{cutName}' has a leg with per-era triggers but no era was given")
            if era not in triggers:
                raise ValueError(f"selection '{selName}': cut '{cutName}' leg defines no triggers for era '{era}'")
            triggers = triggers[era]
        out["hltPaths"] = loadTriggerPaths(triggers) if isinstance(triggers, str) else list(triggers)
    return out


def _resolveThreshold(selName, cutName, bound, value, era):
    """A threshold is either one number, or an object keyed by era."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        if era is None:
            raise ValueError(f"selection '{selName}': cut '{cutName}' has a per-era {bound} but no era was given")
        if era not in value:
            raise ValueError(f"selection '{selName}': cut '{cutName}' has no {bound} for era '{era}'; it defines {sorted(value)}")
        return float(value[era])
    raise ValueError(f"selection '{selName}': cut '{cutName}' has a {bound} that is neither a number nor an object keyed by era")
