"""
Applies a resolved selection to an ntuple and writes an ntuple with the same branches.
"""

# Import Block

## Standard Python imports
import fnmatch
import os
import subprocess
import tempfile

## Third-party
import awkward as ak
import numpy as np
import uproot

## Kamui modules
from .quantities import evaluate


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


def cutMask(cut, events, branches, era):
    """
    The mask a single cut keeps. Returns (mask, note) where note describes what it matched.

    A cut carrying "invert" keeps exactly the events it would otherwise have thrown away,
    which is how an orthogonality veto is written: state the selection the other channel
    makes, then invert it, rather than restating its negation by hand.
    """
    mask, note = _cutMask(cut, events, branches, era)
    if cut.get("invert"):
        return ~mask, f"NOT ({note})"
    return mask, note


def _cutMask(cut, events, branches, era):
    kind = cut["type"]

    if kind == "trigger":
        paths = cut["hltPaths"]
        mask, matched = triggerMask(events, paths, branches)
        return mask, f"{len(matched)}/{len(paths)} paths present"

    if kind == "object":
        ## An existence test, not an object filter: the event is kept when at least one
        ## object satisfies every requirement of some leg. Nothing is removed from the ntuple.
        mask = np.zeros(len(events), dtype=bool)
        notes = []
        for leg in cut["legs"]:
            legMask, note = _legMask(leg, events, branches, era)
            ## A gated leg only counts when its own trigger fired
            if leg.get("hltPaths"):
                fired, matched = triggerMask(events, leg["hltPaths"], branches)
                legMask &= fired
                note = f"({len(matched)} path(s) fired) and " + note
            mask |= legMask
            notes.append(note)
        return mask, " OR ".join(notes)

    if kind == "flags":
        ## Every named flag must be true. A flag absent from the file is reported rather than assumed.
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
        return _conditionMask(cut, events, era), _bounds(cut)

    if kind == "veto":
        paths = cut["hltPaths"]
        fired, matched = triggerMask(events, paths, branches)
        offline = _conditionMask(cut, events, era)
        ## Drop only events that both fired the vetoed trigger and meet every offline condition
        return ~(fired & offline), f"{len(matched)}/{len(paths)} paths present, {_bounds(cut)}"

    if kind == "anyOf":
        ## Each alternative is an ordinary list of cuts that must all hold. The event passes
        ## if any one alternative does. This is how a channel accepts several triggers, each
        ## with its own offline emulation.
        mask = np.zeros(len(events), dtype=bool)
        notes = []
        for option in cut["anyOf"]:
            optionMask = np.ones(len(events), dtype=bool)
            for sub in option["cuts"]:
                subMask, _ = cutMask(sub, events, branches, era)
                optionMask &= subMask
            mask |= optionMask
            notes.append(f"{option['name']} keeps {int(optionMask.sum())}")
        return mask, " OR ".join(notes) if notes else "no alternative applies to this era"

    raise ValueError(f"cut '{cut['name']}' has unknown type '{kind}'")


def _primaryVertex(events):
    """Position of the first vertex passing the standard good-vertex definition."""
    if "PV_isGood" not in events.fields:
        raise ValueError("selection needs branch 'PV_isGood' to identify the primary vertex")
    first = ak.argmax(events["PV_isGood"] == 1, axis=1, keepdims=True)
    return tuple(ak.firsts(events[f"PV_{k}"][first]) for k in ("x", "y", "z"))


def _trackIP(coll, events, wrt):
    """
    Impact parameters computed the way CMSSW does, from the track reference point.

    `dzPV` is the track dz with respect to the primary vertex, and `dxyBS` is the
    track dxy with respect to the beamspot taken at the track's own z, which is what the
    beam tilt correction means. Storing the reference point rather than a precomputed
    impact parameter is what makes both reproducible here.

    The ntuples keep every reconstructed vertex, and the first one is not always a real
    vertex: a fit with ndof below one sits at index 0 often enough to shift dz by a
    centimetre. The primary vertex is the first that passes `PV_isGood`.
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


def _derived(coll, variable, events, era):
    """
    Per-object quantities that are computed rather than stored.

    The ntuples keep raw jet energy fractions instead of a precomputed identification flag,
    so the working point is applied here. select/README.md carries the table.
    """
    if coll == "Jet" and variable == "tightLepVeto":
        from .quantities import tightLepVeto
        return tightLepVeto(events, era)
    if variable == "dzPV":
        return _trackIP(coll, events, "PV")
    if variable == "dxyBeamspot":
        return _trackIP(coll, events, "BS")
    return None


def _oneRequirement(req, coll, events, branches, era, ones):
    """Per-object mask for a single requirement, or for an anyOf group of requirement lists."""
    if "anyOf" in req:
        ## Regions of one collection, ORed per object: an electron satisfies the barrel group
        ## or the endcap group. Without this a region-dependent bound needs a duplicate leg.
        out = None
        for group in req["anyOf"]:
            sub = ones
            for r in group:
                sub = sub & _oneRequirement(r, coll, events, branches, era, ones)
            out = sub if out is None else (out | sub)
        return ones if out is None else out

    name = f"{coll}_{req['variable']}"
    value = _derived(coll, req["variable"], events, era)
    if value is None:
        if name not in branches:
            raise ValueError(f"selection needs branch '{name}', which the ntuple does not have")
        value = events[name]
    keep = ones
    if "min" in req:
        keep = keep & (value >= req["min"])
    if "max" in req:
        keep = keep & (value <= req["max"])
    if "absMin" in req:
        keep = keep & (abs(value) >= req["absMin"])
    if "absMax" in req:
        keep = keep & (abs(value) <= req["absMax"])
    return keep


def _objectMask(leg, events, branches, era):
    """Per-object mask: which objects of a collection satisfy every requirement of this leg."""
    coll = leg["collection"]
    ones = ak.ones_like(events[f"{coll}_pt"], dtype=bool)
    keep = ones
    for req in leg["requirements"]:
        keep = keep & _oneRequirement(req, coll, events, branches, era, ones)
    return keep


# A leg asks whether enough objects of one collection satisfy it. Two requirements cannot be
# written per object: an ordered pT ladder is a statement about the sorted list, and a pair
# requirement is a statement about two objects at once. Both live here rather than in _objectMask.
def _legMask(leg, events, branches, era):
    """Events where a leg is satisfied, and a description of what it asked for."""
    coll = leg["collection"]
    passing = _objectMask(leg, events, branches, era)
    mask = np.asarray(ak.sum(passing, axis=1) >= leg["min"])
    parts = [f"{leg['min']}+ {coll} with " + ", ".join(_reqText(r) for r in leg["requirements"])]

    ladder = leg.get("orderedMinPt")
    if ladder:
        ## The k-th hardest surviving object must clear the k-th threshold, which is how a
        ## multi-jet trigger is written down: QuadPFJet 95/65/60/55.
        pt = ak.sort(events[f"{coll}_pt"][passing], axis=1, ascending=False)
        for k, threshold in enumerate(ladder):
            kth = ak.fill_none(ak.firsts(pt[:, k:k + 1]), -1.0)
            mask &= np.asarray(kth >= threshold)
        parts.append("pT ordered " + "/".join(f"{t:g}" for t in ladder))

    for pair in leg.get("pairRequirements", []):
        value = _derived(coll, pair["variable"], events, era)
        if value is None:
            name = f"{coll}_{pair['variable']}"
            if name not in branches:
                raise ValueError(f"selection needs branch '{name}', which the ntuple does not have")
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
        return "(" + " or ".join(
            "(" + " and ".join(_reqText(r) for r in group) + ")" for group in req["anyOf"]
        ) + ")"
    v = req["variable"]
    parts = []
    if "min" in req:
        parts.append(f"{v} >= {req['min']:g}")
    if "max" in req:
        parts.append(f"{v} <= {req['max']:g}")
    if "absMin" in req:
        parts.append(f"|{v}| >= {req['absMin']:g}")
    if "absMax" in req:
        parts.append(f"|{v}| <= {req['absMax']:g}")
    return " and ".join(parts)


def _conditionMask(cut, events, era):
    """Every condition on a cut must hold."""
    mask = np.ones(len(events), dtype=bool)
    for cond in cut["conditions"]:
        value = evaluate(cond["quantity"], events, era)
        if "min" in cond:
            mask &= np.asarray(value >= cond["min"])
        if "max" in cond:
            mask &= np.asarray(value <= cond["max"])
    return mask


def _bounds(cut):
    parts = []
    for cond in cut["conditions"]:
        if "min" in cond:
            parts.append(f"{cond['quantity']} >= {cond['min']:g}")
        if "max" in cond:
            parts.append(f"{cond['quantity']} <= {cond['max']:g}")
    return " and ".join(parts)


def applySelection(inputPaths, selection, outputPath, writeSteps=False, treeName="Events"):
    """
    Apply every cut in order, write the surviving events, and return the cutflow.

    writeSteps also writes one ntuple per cut, named after the cut, beside the output.
    """
    events, branches = _readAll(inputPaths, treeName)
    total = len(events)

    flow = [{"cut": "input", "type": "", "doc": "Events in the production ntuples, after the trigger skim they were written with", "detail": f"{len(inputPaths)} file(s)",
             "kept": total, "removed": 0, "efficiency": 1.0, "cumulative": 1.0}]
    keep = np.ones(total, dtype=bool)

    for cut in selection["cuts"]:
        before = int(keep.sum())
        mask, note = cutMask(cut, events, branches, selection.get("era"))
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
        if writeSteps:
            stepPath = os.path.join(os.path.dirname(outputPath), f"{cut['name']}.root")
            _write(events[keep], stepPath, treeName)

    _write(events[keep], outputPath, treeName)
    return flow


def _localCopy(path, scratch):
    """
    Bring a remote file local before reading it.

    uproot needs fsspec-xrootd to open a root:// URL directly, and the CMSSW python
    stack does not ship it, so copying first is what works both on a worker and here.
    """
    if not path.startswith("root://"):
        return path, False
    os.makedirs(scratch, exist_ok=True)
    dest = os.path.join(scratch, os.path.basename(path))
    r = subprocess.run(["xrdcp", "-f", "-s", path, dest], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"could not copy {path}: {r.stderr.strip().splitlines()[-1:] or r.returncode}")
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
        raise ValueError("no input files")
    return (parts[0] if len(parts) == 1 else ak.concatenate(parts)), branches


def _write(events, path, treeName):
    """
    Write with one shared counter per collection, the way NanoAOD does it.

    Writing each jagged branch on its own would make uproot emit a counter per branch,
    so a file that went in with nElectron would come out with nElectron_pt, nElectron_eta
    and so on. Grouping the fields of a collection into one record keeps the schema stable
    under repeated selection passes.
    """
    fields = list(events.fields)
    counters = {f[1:] for f in fields if f.startswith("n") and f[1:2].isupper() and f[1:] + "_" not in ("",)}
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
