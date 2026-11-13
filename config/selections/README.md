# Selections

A selection is a JSON file with a list of cuts. `./kamui select` runs it over the ntuples from a `./kamui submit` task and keeps the events that pass every cut, in order. The output ntuples have the same branches as the input, and a cutflow records how many events were left after each cut.

A small example with two cuts:

```json
{
  "cuts": [
    {"name": "metFilters", "type": "flags", "flags": ["Flag_goodVertices", "Flag_eeBadScFilter"]},
    {"name": "oneMuon", "type": "object", "collection": "Muon", "min": 1, "requirements": [{"variable": "pt", "min": <ptMin>}, {"variable": "mediumId", "min": 1}]}
  ]
}
```

Selections sit in a folder per run, `run2/` and `run3/`. Kamui takes the file from the folder that matches each sample's era, so `--selection lepton` gets the Run 2 or Run 3 version by itself.

## What Is Here Now

| File | What it keeps |
|---|---|
| `run2/lepton.json` | Lepton-triggered channel: MET filters, then a single-muon or single-electron trigger that fired, with one lepton on its plateau |
| `run2/displaced.json` | Displacement-triggered channel: high-HT veto, lepton-channel veto, a b-jet or displaced-dijet trigger with offline cuts that mimic it, MET filters |
| `run2/dv3trk.json`, `dv4trk.json`, `dv5trk.json` | One-DV regions: exactly one tight DV with 3, 4, or 5 or more tracks |
| `run2/dv3x3.json`, `dv3x4.json`, `dv3x5.json`, `dv4x4.json`, `dv4x5.json`, `dv5x5.json` | Two-DV regions, named by the track counts of the two DVs. `dv5x5` is the signal region |
| `run3/vbfParking.json`, `run3/bParking.json` | Run 3 trigger studies: only the VBF or single-muon B parking trigger of the sample's era, so the fraction of events kept is the trigger efficiency |

### DV Regions

A region picks events by how many tight DVs they have and how many tracks those DVs carry. `dv3x4`, for example, wants exactly one 4-track DV plus at least one 3-track DV. A tight DV is a high-quality DV: it passes `tightDV` in `config/definitions/`.

Regions don't check triggers, so you run them after a channel:

```
./kamui select --era 2018 --selection lepton,dv3x4 --task myPass --inputTask myNtuples
```

Commas apply the selections in order, in one pass with one cutflow. The ntuples need DVs in them, which `dvFull` and the presets built on it, `dvLepton` and `dvDisplaced`, write in Run 2.

`dv5x5` is blind, so `select` never runs it on data.

## Writing a Selection

### Top-Level Keys

| Key | Meaning |
|---|---|
| **`cuts`** (required) | The cuts, applied in order |
| `eras` (optional) | The eras this file is meant for, as a list |
| `include` (optional) | Selections to build on, as a list. Writing your own `cuts` replaces theirs |
| `blind` (optional, default `false`) | `true` keeps `select` from running this on data, alone or in a comma list |

Any threshold, trigger list or flag list can be one value, or an object keyed by era such as `{"2017": <value2017>, "2018": <value2018>}`. Only the era you run needs to be there.

### Every Cut

| Key | Meaning |
|---|---|
| **`name`** (required) | The cut's name, and its row in the cutflow |
| **`type`** (required) | What it checks, one of the five types below |
| `doc` (optional, default `""`) | A note, printed in the cutflow |
| `invert` (optional, default `false`) | `true` keeps the events the cut would drop |

### Cut Types

| `type` | Keeps an event when | Fields |
|---|---|---|
| `trigger` | Any of the listed HLT paths fired | `triggers` |
| `flags` | Every listed flag is true | `flags` |
| `quantity` | Every condition on an event quantity holds | `conditions`, or one `quantity` with its bounds |
| `object` | Enough objects of one collection pass every requirement, and no more than `max` if it is set | See Object Cuts |
| `anyOf` | At least one alternative passes all its cuts | `anyOf`, a list of alternatives |

- `triggers` is the name of a trigger file in `config/triggers/`, a list of path patterns, or an object keyed by era holding either. A pattern ending in `_v*` loses that suffix and is matched against the branch names, so `HLT_IsoMu24_v*` matches the branch `HLT_IsoMu24`.
- A condition bounds its `quantity` with the same bounds a requirement uses (see Object Cuts). A `quantity` is an event branch such as `MET_pt`, or a count or sum over a collection. `{"collection": "Jet", "requirements": [...]}` counts the jets that pass the requirements, or all jets without them. Add `"sum": "pt"` to sum their pT instead.
- An `anyOf` alternative needs only `cuts`. It can also have a `name` (default `alternative <n>`), a `doc`, and `eras` to use it only in some eras.
- To keep two channels apart, put the other channel's alternatives in an `anyOf` with `invert`. That is how `displaced.json` drops lepton-channel events.

### Object Cuts

| Key | Meaning |
|---|---|
| **`collection`** (required) | Branch prefix, such as `Jet` |
| **`requirements`** (required) | Cuts each object must pass |
| `min` (optional, default `1`) | How many objects must pass, a whole number of at least 1. With `orderedMinPt`, the default is its length. With `max`, it only applies if you write it |
| `max` (optional) | The most objects that may pass, a whole number. `0` vetoes any event that has one |
| `orderedMinPt` (optional) | pT thresholds for the leading passing objects, highest first, such as `[<leadingPtMin>, <secondPtMin>]`. The k-th highest-pT passing object needs a pT at or above the k-th threshold |
| `pairRequirements` (optional) | Cuts on how far apart two passing objects are |

- A requirement bounds one variable, such as `{"variable": "pt", "min": <ptMin>}`. `min`, `max`, `absMin` and `absMax` include the bound; `above`, `below`, `absAbove` and `absBelow` don't. The variable is the branch `<collection>_<variable>`, as `./kamui content` lists it.
- Kamui computes `dxyBeamspot` and `dzPV` for you from the track reference point: dxy to the beamspot at the object's own z (beam tilt included), and dz to the first PV that passes `PV_isGood`.
- The same variable can appear twice, and both bounds apply. Use this to take a shared definition and tighten one of its cuts.
- `{"definition": "<name>"}` pulls in a definition from `config/definitions/`. `{"anyOf": [[...], [...]]}` passes an object that passes every requirement in at least one of the groups.
- `pairRequirements` put `absDiffMin` and `absDiffMax` on one variable, and pass when at least one pair does.

## Relevant Commands

- `./kamui selection` lists the selections. `./kamui selection lepton,dv3x4 --era 2018` shows one exactly as `select` will apply it.
- `./kamui select` runs a selection on a production task's ntuples, and `./kamui cutflow` shows what each cut kept.
- Run `./kamui check` after editing anything here.

The flags and worked examples are in `python/kamui/README.md`.

## Caveats

- An `anyOf` inside `requirements` lets each object pass a different group, and they all count toward `min`. An `anyOf` cut whose alternatives each hold one object cut needs `min` objects passing a single alternative. The two agree only when `min` is 1.
- The `DV` collection holds every DV the vertexer finds, even ones outside the beampipe or with a NaN `dBVErr`, which JMTucker never counts. Build your own DV cuts on `tightDV`, or give them an `insideBeampipe` requirement and a `dBVErr` bound.
- The two-DV regions follow JMTucker's definitions:
  - They can overlap: tight DVs of 4, 5 and 6 tracks put an event in both `dv4x5` and `dv5x5`.
  - `dv3x5` drops events that also hold a tight 4-track DV, so it never shares an event with `dv4x5`.
  - `dv3x5` and `dv4x5` count only DVs with exactly 5 tracks, so an event whose tight DVs have 3 and 6 tracks, or 4 and 6, lands in no two-DV region (`Bugs/jmtucker/adapted/fiveTrackCappedAtFive.md`).
- The Run 2 selections have to keep matching JMTucker. After any change, check the yields against JMTucker again.
- `displaced.json`'s `leptonVeto` is `lepton.json`'s `leptonPlateau` inverted. Each file writes out its own trigger lists, so keep them the same, or events land in both channels or in neither.
