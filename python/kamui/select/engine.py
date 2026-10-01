"""
Applies a resolved selection to an ntuple and writes an ntuple with the same branches.
"""

# Import Block

## Standard Python imports
import fnmatch
import operator
import os
import subprocess
import tempfile

## Third-party
import awkward as ak
import numpy as np
import uproot

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
    kind = cut["type"]

    if kind == "trigger":
        paths = cut["hltPaths"]
        mask, matched = triggerMask(events, paths, branches)
        return mask, f"{len(matched)}/{len(paths)} paths present"

    if kind == "object":
        ## The event is kept when enough objects satisfy the requirements. Nothing is removed from the ntuple.
        return _legMask(cut, events, branches)

    if kind == "flags":
        ## Every named flag must be true, and a flag absent from the file is skipped and reported as MISSING
        missing = [f for f in cut["flags"] if f not in branches]
        mask = np.ones(len(events), dtype=bool)
        for f in cut["flags"]:
            if f in branches:
                mask &= np.asarray(events[f])
        note = f"{len(cut['flags']) - len(missing)}/{len(cut['flags'])} flags present"
        if missing:
            note += f", MISSING {missing}"
        return mask, note

    if kind == "quantity":
        return _conditionMask(cut, events, branches), _bounds(cut)

    if kind == "anyOf":
        ## Each alternative is a list of cuts that must all hold, which lets a channel accept several triggers, each with its own offline emulation
        mask = np.zeros(len(events), dtype=bool)
        notes = []
        for option in cut["anyOf"]:
            optionMask = np.ones(len(events), dtype=bool)
            for sub in option["cuts"]:
                subMask, _ = cutMask(sub, events, branches)
                optionMask &= subMask
            mask |= optionMask
            notes.append(f"{option['name']} keeps {int(optionMask.sum())}")
        return mask, " OR ".join(notes) if notes else "no alternative applies to this era"

    raise ValueError(f"Cut '{cut['name']}' has unknown type '{kind}'")


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


def _derived(coll, variable, events):
    """Per-object quantities computed from stored branches."""
    if variable == "dzPV":
        return _trackIP(coll, events, "PV")
    if variable == "dxyBeamspot":
        return _trackIP(coll, events, "BS")
    return None


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
        raise ValueError(f"Selection needs collection '{coll}', which the ntuple does not have")
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


def applySelection(inputPaths, selection, outputPath, treeName="Events"):
    """Apply every cut in order, write the surviving events, and return the cutflow."""
    events, branches = _readAll(inputPaths, treeName)
    total = len(events)

    flow = [{"cut": "input", "type": "", "doc": "Events in the production ntuples, after the trigger skim they were written with", "detail": f"{len(inputPaths)} file(s)",
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


def _readAll(inputPaths, treeName):
    """Read every input file into one array. Returns (events, branchNames)."""
    parts = []
    branches = None
    scratch = os.path.join(tempfile.gettempdir(), "kamuiSelectInputs")
    fetched = []
    try:
        for p in inputPaths:
            local, isCopy = _localCopy(p, scratch)
            if isCopy:
                fetched.append(local)
            with uproot.open(local) as f:
                tree = f[treeName]
                if branches is None:
                    branches = [k for k in tree.keys()]
                parts.append(tree.arrays())
    finally:
        for f in fetched:
            try:
                os.remove(f)
            except OSError:
                pass
    if not parts:
        raise ValueError("No input files")
    return (parts[0] if len(parts) == 1 else ak.concatenate(parts)), branches


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
