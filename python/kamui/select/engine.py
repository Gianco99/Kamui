"""
Applies a resolved selection to an ntuple and writes an ntuple with the same branches.
"""

# Import Block

## Standard Python imports
import fnmatch
import operator
import os
import re
import shutil
import subprocess
import tempfile

## Third-party
import awkward as ak
import numpy as np
import uproot

## Kamui modules
from ..configReaders.selections import CUT_TYPES

## How each bound compares: whether it reads the absolute value, and the comparison it makes
COMPARISONS = {
    "min":      (False, operator.ge),
    "max":      (False, operator.le),
    "absMin":   (True,  operator.ge),
    "absMax":   (True,  operator.le),
    "above":    (False, operator.gt),
    "below":    (False, operator.lt),
    "absAbove": (True,  operator.gt),
    "absBelow": (True,  operator.lt),
}
SYMBOLS = {operator.ge: ">=", operator.le: "<=", operator.gt: ">", operator.lt: "<"}

## The counts inside a cutflow note that add up over jobs: the events an anyOf alternative keeps, and the input files
_ADDITIVE = re.compile(r"(?<= keeps )\d+|^\d+(?= file\(s\)$)")


class MissingCollections(ValueError):
    """The ntuple lacks collections the selection reads."""

    def __init__(self, collections):
        self.collections = list(collections)
        super().__init__(f"Selection needs collection(s) {', '.join(self.collections)}, which the ntuple does not have")


class NoTriggerPath(ValueError):
    """A trigger cut matched none of its paths."""


def triggerMask(events, patterns, branches):
    """True where any branch matching one of the patterns is true. A pattern matching nothing contributes nothing."""
    matched = []
    for pattern in patterns:
        stem = pattern[:-3] if pattern.endswith("_v*") else pattern
        for b in branches:
            if b == stem or fnmatch.fnmatch(b, stem):
                matched.append(b)
    matched = sorted(set(matched))
    if not matched:
        return np.zeros(len(events), dtype=bool), []
    mask = np.zeros(len(events), dtype=bool)
    for b in matched:
        mask |= np.asarray(events[b])
    return mask, matched


def cutMask(cut, events, branches):
    """
    The mask a single cut keeps, returned as (mask, note) where note describes what it matched.

    A cut carrying "invert" keeps exactly the events it would otherwise have thrown away. An orthogonality veto is the other channel's selection, inverted.
    """
    mask, note = _cutMask(cut, events, branches)
    if cut.get("invert"):
        return ~mask, f"NOT ({note})"
    return mask, note


def _cutMask(cut, events, branches):
    apply = CUT_MASKS.get(cut["type"])
    if apply is None:
        raise ValueError(f"Cut '{cut['name']}' has unknown type '{cut['type']}'")
    return apply(cut, events, branches)


# A path can be missing from part of an era's menu, so one unmatched pattern is normal. A cut matching none of its patterns can never fire, which only a wrong era or a misspelled list explains.
def _triggerCut(cut, events, branches):
    """Events where any of the cut's HLT paths fired."""
    paths = cut["hltPaths"]
    mask, matched = triggerMask(events, paths, branches)
    if not matched:
        raise NoTriggerPath(f"Cut '{cut['name']}' matches none of its trigger paths {paths} in the ntuple, so it can never fire. Check the era and the trigger list.")
    return mask, f"{len(matched)}/{len(paths)} paths present"


def _flagsCut(cut, events, branches):
    """Events where every named flag is true. A flag the ntuple lacks would otherwise pass every event, so it is an error."""
    missing = [f for f in cut["flags"] if f not in branches]
    if missing:
        raise ValueError(f"Cut '{cut['name']}' needs flag(s) {missing}, which the ntuple does not have. Check the spelling and the era.")
    mask = np.ones(len(events), dtype=bool)
    for f in cut["flags"]:
        mask &= np.asarray(events[f])
    return mask, f"{len(cut['flags'])}/{len(cut['flags'])} flags present"


def _quantityCut(cut, events, branches):
    """Events where every condition on an event quantity holds."""
    return _conditionMask(cut, events, branches), _bounds(cut)


def _anyOfCut(cut, events, branches):
    """
    Events passing at least one alternative, each a list of cuts that must all hold. This lets a channel accept several triggers, each with its own offline emulation.

    A trigger path missing from the ntuple counts as not fired inside an alternative, since part of an era can run without that path. The cut fails only when every alternative is missing a path.
    """
    mask = np.zeros(len(events), dtype=bool)
    notes = []
    absent = 0
    for option in cut["anyOf"]:
        optionMask = np.ones(len(events), dtype=bool)
        missingPath = False
        for sub in option["cuts"]:
            try:
                subMask, _ = cutMask(sub, events, branches)
            except NoTriggerPath:
                subMask = np.full(len(events), bool(sub.get("invert")))
                missingPath = True
            optionMask &= subMask
        absent += missingPath
        mask |= optionMask
        notes.append(f"{option['name']} keeps {int(optionMask.sum())}")
    if absent and absent == len(cut["anyOf"]):
        raise NoTriggerPath(f"Cut '{cut['name']}': no alternative has its trigger path in the ntuple, so it can never fire. Check the era and the trigger lists.")
    return mask, " OR ".join(notes) if notes else "no alternative applies to this era"


def _primaryVertex(events):
    """Position of the first vertex passing the standard good-vertex definition."""
    if "PV_isGood" not in events.fields:
        raise ValueError("Selection needs branch 'PV_isGood' to identify the primary vertex")
    first = ak.argmax(events["PV_isGood"] == 1, axis=1, keepdims=True)
    return tuple(ak.firsts(events[f"PV_{k}"][first]) for k in ("x", "y", "z"))


def _trackIP(coll, events, wrt):
    """
    Impact parameters computed the way CMSSW does, from the track reference point the ntuples store.

    `dzPV` is dz to the primary vertex, and `dxyBeamspot` is dxy to the beamspot at the track's own z, which applies the beam tilt. The primary vertex is the first passing `PV_isGood`, since a fit with ndof below one sits at index 0 often enough to shift dz by a centimeter.
    """
    px = events[f"{coll}_pt"] * np.cos(events[f"{coll}_phi"])
    py = events[f"{coll}_pt"] * np.sin(events[f"{coll}_phi"])
    pz = events[f"{coll}_pt"] * np.sinh(events[f"{coll}_eta"])
    pt = events[f"{coll}_pt"]
    vx, vy, vz = events[f"{coll}_vx"], events[f"{coll}_vy"], events[f"{coll}_vz"]

    if wrt == "PV":
        rx, ry, rz = _primaryVertex(events)
        return (vz - rz) - ((vx - rx) * px + (vy - ry) * py) / pt * (pz / pt)

    ## Beamspot at the track's z, following the beam tilt
    bx = events["BeamSpot_x"] + events["BeamSpot_dxdz"] * (vz - events["BeamSpot_z"])
    by = events["BeamSpot_y"] + events["BeamSpot_dydz"] * (vz - events["BeamSpot_z"])
    return (-(vx - bx) * py + (vy - by) * px) / pt


## Per-object variables computed from stored branches, each with the collections it reads besides its own
DERIVED_VARIABLES = {
    "dzPV":        (lambda coll, events: _trackIP(coll, events, "PV"), ("PV",)),
    "dxyBeamspot": (lambda coll, events: _trackIP(coll, events, "BS"), ("BeamSpot",)),
}


def _derived(coll, variable, events):
    """A computed per-object variable, or None when the variable is a stored branch."""
    entry = DERIVED_VARIABLES.get(variable)
    return entry[0](coll, events) if entry else None


def _oneRequirement(req, coll, events, branches, ones):
    """Per-object mask for a single requirement, or for an anyOf group of requirement lists."""
    if "anyOf" in req:
        ## Groups are ORed per object, so one leg can carry region-dependent bounds such as an electron's barrel and endcap cuts
        out = None
        for group in req["anyOf"]:
            sub = ones
            for r in group:
                sub = sub & _oneRequirement(r, coll, events, branches, ones)
            out = sub if out is None else (out | sub)
        return ones if out is None else out

    name = f"{coll}_{req['variable']}"
    value = _derived(coll, req["variable"], events)
    if value is None:
        if name not in branches:
            raise ValueError(f"Selection needs branch '{name}', which the ntuple does not have")
        value = events[name]
    return _within(value, req, ones)


def _within(value, bounds, keep):
    """Mask of the values inside every bound given."""
    for bound, (useAbs, compare) in COMPARISONS.items():
        if bound in bounds:
            keep = keep & compare(abs(value) if useAbs else value, bounds[bound])
    return keep


def _boundsText(name, bounds):
    return " and ".join(f"{'|' + name + '|' if useAbs else name} {SYMBOLS[compare]} {bounds[bound]:g}" for bound, (useAbs, compare) in COMPARISONS.items() if bound in bounds)


def _objectMask(leg, events, branches):
    """Per-object mask: which objects of a collection satisfy every requirement of this leg."""
    coll = leg["collection"]
    first = next((b for b in branches if b.startswith(coll + "_")), None)
    if first is None:
        raise MissingCollections([coll])
    ones = ak.ones_like(events[first], dtype=bool)
    keep = ones
    for req in leg["requirements"]:
        keep = keep & _oneRequirement(req, coll, events, branches, ones)
    return keep


# Ordered pT ladders and pair requirements live here, since they read the sorted list and two objects at once
def _legMask(leg, events, branches):
    """Events where a leg is satisfied, and a description of what it asked for."""
    coll = leg["collection"]
    passing = _objectMask(leg, events, branches)
    mask = np.asarray(ak.sum(passing, axis=1) >= leg["min"])
    parts = [f"{leg['min']}+ {coll} with " + ", ".join(_reqText(r) for r in leg["requirements"])]

    ladder = leg.get("orderedMinPt")
    if ladder:
        ## The k-th hardest surviving object must clear the k-th threshold, which is how a multi-jet trigger such as QuadPFJet 95/65/60/55 is written
        pt = ak.sort(events[f"{coll}_pt"][passing], axis=1, ascending=False)
        for k, threshold in enumerate(ladder):
            kth = ak.fill_none(ak.firsts(pt[:, k:k + 1]), -1.0)
            mask &= np.asarray(kth >= threshold)
        parts.append("pT ordered " + "/".join(f"{t:g}" for t in ladder))

    for pair in leg.get("pairRequirements", []):
        value = _derived(coll, pair["variable"], events)
        if value is None:
            name = f"{coll}_{pair['variable']}"
            if name not in branches:
                raise ValueError(f"Selection needs branch '{name}', which the ntuple does not have")
            value = events[name]
        left, right = ak.unzip(ak.combinations(value[passing], 2))
        separation = abs(left - right)
        ok = ak.ones_like(separation, dtype=bool)
        if "absDiffMax" in pair:
            ok = ok & (separation <= pair["absDiffMax"])
        if "absDiffMin" in pair:
            ok = ok & (separation >= pair["absDiffMin"])
        mask &= np.asarray(ak.any(ok, axis=1))
        parts.append(_pairText(pair))

    return mask, " and ".join(parts)


def _pairText(pair):
    v = pair["variable"]
    parts = []
    if "absDiffMax" in pair:
        parts.append(f"some pair with |d{v}| <= {pair['absDiffMax']:g}")
    if "absDiffMin" in pair:
        parts.append(f"some pair with |d{v}| >= {pair['absDiffMin']:g}")
    return " and ".join(parts)


def _reqText(req):
    if "anyOf" in req:
        return "(" + " or ".join("(" + " and ".join(_reqText(r) for r in group) + ")" for group in req["anyOf"]) + ")"
    return _boundsText(req["variable"], req)


def _quantity(q, events, branches):
    """An event branch by name, or a count or sum over the objects of a collection passing requirements."""
    if isinstance(q, str):
        if q not in branches:
            raise ValueError(f"Selection needs branch '{q}', which the ntuple does not have")
        return events[q]
    passing = _objectMask(q, events, branches)
    if "sum" not in q:
        return ak.sum(passing, axis=1)
    name = f"{q['collection']}_{q['sum']}"
    if name not in branches:
        raise ValueError(f"Selection needs branch '{name}', which the ntuple does not have")
    return ak.sum(events[name][passing], axis=1)


def _quantityText(q):
    if isinstance(q, str):
        return q
    text = f"sum of {q['collection']} {q['sum']}" if "sum" in q else f"number of {q['collection']}"
    if q["requirements"]:
        text += " with " + ", ".join(_reqText(r) for r in q["requirements"])
    return text


def _conditionMask(cut, events, branches):
    """Every condition on a cut must hold."""
    mask = np.ones(len(events), dtype=bool)
    for cond in cut["conditions"]:
        value = _quantity(cond["quantity"], events, branches)
        mask &= np.asarray(_within(value, cond, True))
    return mask


def _bounds(cut):
    return " and ".join(_boundsText(_quantityText(cond["quantity"]), cond) for cond in cut["conditions"])


## The function applying each cut type. Its keys must be the CUT_TYPES the readers accept, so a new cut type needs a function here too.
CUT_MASKS = {
    "trigger":  _triggerCut,
    "flags":    _flagsCut,
    "quantity": _quantityCut,
    "object":   _legMask,
    "anyOf":    _anyOfCut,
}
if set(CUT_MASKS) != set(CUT_TYPES):
    raise RuntimeError(f"Cut types {sorted(set(CUT_MASKS) ^ set(CUT_TYPES))} are in only one of CUT_TYPES (configReaders/selections.py) and CUT_MASKS (select/engine.py)")


def collectionsUsed(selection):
    """Every collection a resolved selection reads, so a pass can refuse ntuples lacking one before reading them."""
    found = set()

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("collection"), str):
                found.add(node["collection"])
            if node.get("variable") in DERIVED_VARIABLES:
                found.update(DERIVED_VARIABLES[node["variable"]][1])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(selection["cuts"])
    return sorted(found)


def mergeNotes(notes):
    """The note for one cut over several jobs. The counts in an anyOf or input note are summed, and any other note is kept when every job agrees."""
    texts = {tuple(_ADDITIVE.split(n)) for n in notes}
    if len(texts) != 1:
        return "Differs between jobs: " + " | ".join(sorted(set(notes)))
    text = texts.pop()
    sums = [sum(column) for column in zip(*([int(c) for c in _ADDITIVE.findall(n)] for n in notes))]
    return "".join(piece + (str(sums[i]) if i < len(sums) else "") for i, piece in enumerate(text))


def applySelection(inputPaths, selection, outputPath, treeName="Events"):
    """Apply every cut in order, write the surviving events, and return the cutflow."""
    events, branches = _readAll(inputPaths, treeName, collectionsUsed(selection))
    total = len(events)

    flow = [{"cut": "input", "type": "", "doc": "Events in the production ntuples, after any trigger skim they were written with", "detail": f"{len(inputPaths)} file(s)",
             "kept": total, "removed": 0, "efficiency": 1.0, "cumulative": 1.0}]
    keep = np.ones(total, dtype=bool)

    for cut in selection["cuts"]:
        before = int(keep.sum())
        mask, note = cutMask(cut, events, branches)
        keep &= mask
        after = int(keep.sum())
        flow.append({
            "cut": cut["name"],
            "type": cut["type"],
            "doc": cut.get("doc", ""),
            "detail": note,
            "kept": after,
            "removed": before - after,
            "efficiency": (after / before) if before else 0.0,
            "cumulative": (after / total) if total else 0.0,
        })

    _write(events[keep], outputPath, treeName)
    return flow


def _localCopy(path, scratch):
    """Bring a remote file local before reading it, since uproot needs fsspec-xrootd to open a root:// URL and the CMSSW Python stack does not ship it."""
    if not path.startswith("root://"):
        return path, False
    os.makedirs(scratch, exist_ok=True)
    dest = os.path.join(scratch, os.path.basename(path))
    r = subprocess.run(["xrdcp", "-f", "-s", path, dest], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Could not copy {path}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
    return dest, True


def _isTriggerBit(branch):
    """Whether a branch holds one trigger or flag decision. NanoAOD gives each one this title, and the name test covers ntuples a selection pass rewrote, which carry no titles."""
    return branch.title.startswith("Trigger/flag bit") or branch.name.startswith(("HLT_", "Flag_"))


def _fewNames(names, shown=5):
    names = sorted(names)
    return ", ".join(names[:shown]) + (f" and {len(names) - shown} more" if len(names) > shown else "")


# Each read gets its own scratch directory, since a shared one breaks for a second user on the node and lets parallel passes over the same task delete each other's copies.
def _readAll(inputPaths, treeName, collections=()):
    """
    Read every input file into one array. Returns (events, branchNames), where branchNames is every branch any file has.

    Files written under different HLT menus carry different trigger and flag decisions, so a decision a file lacks reads as False in its events. Every other branch must be in every file. Raises MissingCollections from the first file's branches, before reading the rest.
    """
    parts = []
    branches = None
    scratch = tempfile.mkdtemp(prefix="kamuiSelect")
    try:
        for p in inputPaths:
            local, isCopy = _localCopy(p, scratch)
            with uproot.open(local) as f:
                tree = f[treeName]
                names = list(tree.keys())
                others = {b for b in names if not _isTriggerBit(tree[b])}
                if branches is None:
                    branches, first, firstOthers = list(names), p, others
                    missing = [c for c in collections if not any(b.startswith(c + "_") for b in branches)]
                    if missing:
                        raise MissingCollections(missing)
                elif others != firstOthers:
                    lacks = [f"{name} lacks {_fewNames(gone)}" for name, gone in ((p, firstOthers - others), (first, others - firstOthers)) if gone]
                    raise ValueError(f"Input files {first} and {p} hold different branches besides trigger and flag decisions ({'; '.join(lacks)}), so they cannot be read as one sample. Check that every input comes from the same production.")
                seen = set(branches)
                branches += [b for b in names if b not in seen]
                parts.append(tree.arrays())
            if isCopy:
                os.remove(local)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if not parts:
        raise ValueError("No input files")
    if len(parts) == 1:
        return parts[0], branches
    for i, part in enumerate(parts):
        if list(part.fields) != branches:
            present = set(part.fields)
            parts[i] = ak.zip({b: part[b] if b in present else np.zeros(len(part), dtype=bool) for b in branches}, depth_limit=1)
    return ak.concatenate(parts), branches


def _write(events, path, treeName):
    """Write with one shared counter per collection, the way NanoAOD does it, so the schema stays stable under repeated selection passes."""
    fields = list(events.fields)
    counters = {f[1:] for f in fields if f.startswith("n") and f[1:2].isupper()}
    collections = sorted(c for c in counters if any(f.startswith(c + "_") for f in fields))

    grouped = {}
    used = set()
    for c in collections:
        members = {f[len(c) + 1:]: events[f] for f in fields if f.startswith(c + "_")}
        if not members:
            continue
        grouped[c] = ak.zip(members)
        used.add("n" + c)
        used.update(f for f in fields if f.startswith(c + "_"))

    for f in fields:
        if f not in used:
            grouped[f] = events[f]

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with uproot.recreate(path) as f:
        f.mktree(treeName, {k: v.type for k, v in grouped.items()}, counter_name=lambda name: "n" + name)
        f[treeName].extend(grouped)
