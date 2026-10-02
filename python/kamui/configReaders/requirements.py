"""
The per-object requirement grammar that selections, definitions and the vertexer's jets share.
"""

# Import Block

## Standard Python imports
import os

## Kamui modules
from ..foundations import paths
from ..foundations.config import RUNS, loadWithIncludes, runDir

## Every bound a requirement may carry. min and max are inclusive, above and below exclusive.
BOUNDS = ("min", "max", "absMin", "absMax", "above", "below", "absAbove", "absBelow")

## Every key one per-object requirement may carry
REQUIREMENT_FIELDS = set(BOUNDS) | {"variable", "anyOf", "definition"}

## How each bound reads as a C++ cut on the expression behind a variable
CUT_FORMS = {
    "min":      "{expr} >= {value}",
    "max":      "{expr} <= {value}",
    "absMin":   "abs({expr}) >= {value}",
    "absMax":   "abs({expr}) <= {value}",
    "above":    "{expr} > {value}",
    "below":    "{expr} < {value}",
    "absAbove": "abs({expr}) > {value}",
    "absBelow": "abs({expr}) < {value}",
}


def listDefinitions(definitionDir=None):
    """Every definition config, by name."""
    definitionDir = definitionDir or paths.DEFINITIONS_DIR
    if not os.path.isdir(definitionDir):
        return []
    return sorted(f[:-5] for f in os.listdir(definitionDir) if f.endswith(".json"))


def definitionFiles(definitionDir=None):
    """Every definition as (run, folder, name), from one folder per run."""
    definitionDir = definitionDir or paths.DEFINITIONS_DIR
    return [(r, os.path.join(definitionDir, r), n) for r in RUNS for n in listDefinitions(os.path.join(definitionDir, r))]


def definitionEras(name, definitionDir=None):
    """The eras a definition is keyed by, or None when one list serves every era."""
    reqs = loadWithIncludes(name, definitionDir or paths.DEFINITIONS_DIR).get("requirements")
    return sorted(reqs) if isinstance(reqs, dict) else None


def resolveThreshold(where, bound, value, era):
    """A threshold is either one number, or an object keyed by era."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        if era is None:
            raise ValueError(f"{where} has a per-era {bound} but no era was given")
        if era not in value:
            raise ValueError(f"{where} has no {bound} for era '{era}'; it defines {sorted(value)}")
        return float(value[era])
    raise ValueError(f"{where} has a {bound} that is neither a number nor an object keyed by era")


def resolveRequirements(where, reqs, era, definitionDir=None):
    """A requirement list with every definition expanded and every era-dependent bound resolved."""
    if not isinstance(reqs, list) or not reqs:
        raise ValueError(f"{where} has no requirements")
    out = []
    for req in reqs:
        out += _resolveOne(where, req, era, definitionDir)
    return out


def _resolveOne(where, req, era, definitionDir):
    if not isinstance(req, dict):
        raise ValueError(f"{where} has a requirement that is not an object")
    bad = sorted(set(req) - REQUIREMENT_FIELDS)
    if bad:
        raise ValueError(f"{where} has a requirement with unknown key(s) {bad}; valid keys are {sorted(REQUIREMENT_FIELDS)}")

    if "definition" in req:
        if len(req) != 1:
            raise ValueError(f"{where} has a requirement mixing 'definition' with {sorted(set(req) - {'definition'})}")
        name = req["definition"]
        reqs = loadWithIncludes(name, definitionDir or runDir(paths.DEFINITIONS_DIR, era)).get("requirements")
        if isinstance(reqs, dict):
            if era is None:
                raise ValueError(f"{where} uses definition '{name}', which is keyed by era, but no era was given")
            if era not in reqs:
                raise ValueError(f"Definition '{name}' defines no requirements for era '{era}'; it defines {sorted(reqs)}")
            reqs = reqs[era]
        return resolveRequirements(f"Definition '{name}'", reqs, era, definitionDir)

    if "anyOf" in req:
        if len(req) != 1:
            raise ValueError(f"{where} has a requirement mixing 'anyOf' with {sorted(set(req) - {'anyOf'})}")
        groups = req["anyOf"]
        if not isinstance(groups, list) or len(groups) < 2:
            raise ValueError(f"{where} has a requirement 'anyOf' that is not a list of at least two groups")
        return [{"anyOf": [resolveRequirements(where, g, era, definitionDir) for g in groups]}]

    if "variable" not in req:
        raise ValueError(f"{where} has a requirement with no 'variable'")
    resolved = {"variable": req["variable"]}
    for bound in BOUNDS:
        if bound in req:
            resolved[bound] = resolveThreshold(where, bound, req[bound], era)
    if len(resolved) == 1:
        raise ValueError(f"{where} requirement on '{req['variable']}' has no bound")
    return [resolved]


def cutString(reqs, exprs, where):
    """The resolved requirements as one C++ cut, each variable replaced by the expression that defines it."""
    terms = []
    for req in reqs:
        if "anyOf" in req:
            terms.append("(" + " || ".join("(" + cutString(g, exprs, where) + ")" for g in req["anyOf"]) + ")")
            continue
        if req["variable"] not in exprs:
            raise ValueError(f"{where} requires '{req['variable']}', which is not a variable of the collection defining them")
        expr = exprs[req["variable"]]
        if any(ch in expr for ch in " ?+-*/"):
            expr = "(" + expr + ")"
        for bound in BOUNDS:
            if bound in req:
                terms.append(CUT_FORMS[bound].format(expr=expr, value=req[bound]))
    return " && ".join(terms)
