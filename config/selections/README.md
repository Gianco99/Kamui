# Selection Documentation

A selection JSON is an ordered list of event-level cuts, applied in the order they are listed. `./kamui select` runs one over the ntuples a `./kamui submit` task wrote, and writes out ntuples with the same branches holding only the events that pass. It also writes a cutflow: the number of events left after each cut, in the same order. Each cut has a `type`, such as `trigger` or `object`, that says what it checks.

| File | Channel |
|---|---|
| `run2/lepton.json` | Run 2 lepton-triggered channel: MET filters, then a single-muon or single-electron path that fired with one lepton on its plateau |
| `run2/displaced.json` | Run 2 displacement-triggered channel: high-HT veto, lepton-channel veto, a b-jet or displaced-dijet path that fired along with offline cuts that mimic it, MET filters |
| `run2/dv3trk.json`, `dv4trk.json`, `dv5trk.json` | One-DV regions: exactly one tight DV with 3, 4, or 5 or more tracks |
| `run2/dv3x3.json`, `dv3x4.json`, `dv3x5.json`, `dv4x4.json`, `dv4x5.json`, `dv5x5.json` | Two-DV regions, named by the track counts of two tight DVs. `dv5x5` is the signal region and is blind |
| `run3/vbfParking.json`, `run3/bParking.json` | Run 3 trigger studies: only a cut on the VBF or single-muon B parking paths of the sample's era, so the fraction of events kept is the trigger efficiency |

A tight DV passes the `tightDV` definition in `config/definitions/`. The DV regions hold no channel cuts, so they run stacked after a channel: `--selection lepton,dv3x4` applies `lepton.json`'s cuts and then `dv3x4.json`'s, with one cutflow.

In Run 2, `dvFull` carries the DV collections, and so do `dvLepton` and `dvDisplaced`, which build on it.

Selections sit in a folder per run. A selection pass reads the file of that name from the run folder of each sample's era, so `--selection lepton` picks the Run 2 or Run 3 file to match the samples.
## File Structure

| Key | Meaning |
|---|---|
| **`cuts`** (required, default: None) | The ordered cut list |
| `eras` (optional, default: None) | The list of eras this config is meant for |
| `include` (optional, default: None) | A list of selection config names to build on. Naming `cuts` replaces the inherited list |
| `blind` (optional, default: `false`) | When true, `./kamui select` refuses to run this selection on data, alone or stacked. A selection that asks for the signal region, as `SIGNAL_REGION` in `python/kamui/configReaders/selections.py` defines it, has to set it, or Kamui stops with an error |

Any threshold, trigger list or flag list may be written as a single value or as an object keyed by era. Only the era being run has to appear.
## Cuts

Every cut carries these, whatever its type:

| Key | Meaning |
|---|---|
| **`name`** (required, default: None) | Names the cut, and its row in the cutflow |
| **`type`** (required, default: None) | One of the five below |
| `doc` (optional, default: `""`) | Free text, echoed into the cutflow |
| `invert` (optional, default: `false`) | Keeps exactly the events the cut would otherwise drop |

A cut takes only these keys and the fields its type lists below. Any other key is an error.

## Cut Types

| `type` | Keeps an event when | Fields |
|---|---|---|
| `trigger` | Any of the named HLT paths fired | `triggers` |
| `flags` | Every named branch is true. A flag the ntuple lacks stops the pass | `flags` |
| `quantity` | Every condition on an event quantity holds | `conditions`, or a single `quantity` with its bounds |
| `object` | Enough objects of one collection satisfy every requirement, and no more than `max` when it is set | `collection`, `requirements`, and the fields under Object Cuts |
| `anyOf` | At least one alternative passes all of its cuts | `anyOf` list of alternatives |

Some details regarding these cut types:

- `triggers` is the name of a config with `mode` `any` in the era's run folder of `config/triggers/`, an explicit list of path patterns, or an object keyed by era holding either. 
  - A pattern ending in `_v*` has that suffix stripped and is matched against the ntuple's branch names.
  - A `trigger` cut none of whose patterns matches a branch stops the pass, since it could never fire. Inside an `anyOf` alternative, a path the ntuple lacks counts as not fired, because part of an era can run without it, and the `anyOf` stops the pass only when every alternative lacks its path.

- A condition bounds one `quantity` with the same bounds a requirement uses, listed under Object Cuts. The `quantity` is an event branch, such as `MET_pt`, or a count or sum over a collection. `{"collection": "Jet", "requirements": [...]}` counts the objects passing the requirements, or every object when `requirements` is left out. Adding `"sum": "pt"` sums that variable over the same objects.

- An `anyOf` alternative needs only `cuts`; `name` defaults to `alternative <n>`, and `doc` and `eras`, the list of eras it applies to, are optional. Any other key is an error.

- To keep a channel orthogonal to another, put the other channel's alternatives in an `anyOf` with `invert`, which drops every event the other channel would keep.

## Object Cuts

An `object` cut asks how many objects of one collection satisfy every requirement.

| Key | Meaning |
|---|---|
| **`collection`** (required, default: None) | Branch prefix, such as `Jet` |
| **`requirements`** (required, default: None) | Per-object requirements, all ANDed |
| `min` (optional, default: the length of `orderedMinPt`, or 1) | How many objects must satisfy the requirements, a whole number of at least 1 |
| `max` (optional, default: None) | The most objects that may satisfy the requirements, a whole number. `0` drops every event holding one. With `max`, `min` applies only when written, `orderedMinPt` and `pairRequirements` are not allowed, and the cutflow shows the cut as a `quantity` count |
| `orderedMinPt` (optional, default: None) | pT thresholds in descending order: the k-th highest-pT passing object needs pT at or above the k-th threshold |
| `pairRequirements` (optional, default: None) | Requirements on two surviving objects at once |

- A requirement names a `variable` and bounds it with `min`, `max`, `absMin` or `absMax`, which are inclusive, or `above`, `below`, `absAbove` or `absBelow`, which are exclusive.
  - It reads the branch `<collection>_<variable>`, one of the names `./kamui content` lists under Branches for that collection.
  - `dxyBeamspot` and `dzPV` are computed from the track reference point: dxy with respect to the beamspot at the object's own z, following the beam tilt, and dz with respect to the first PV passing `PV_isGood`.
- When the same variable appears twice, both bounds apply. This lets a cut name a shared definition and then add a harder threshold of its own, such as a higher pT for one trigger path.
- A requirement can also be `{"definition": "<name>"}`, which stands for the cuts of that definition in `config/definitions/`. It can also be `{"anyOf": [[...], [...]]}`, which an object passes when it passes every requirement in at least one group.
- `pairRequirements` bound how far apart two passing objects are in one `variable`, using `absDiffMin` and `absDiffMax`, and pass when at least one pair does.

## Relevant Commands

- Use `selection` to list the selections, or to see one resolved for an era as `select` applies it.
- Use `select` to apply one of these to a production task's ntuples.
- Use `cutflow` to read what each cut kept afterwards.
- Run `check` after editing anything here.

See `python/kamui/README.md` for the flags and worked examples.

## Caveats

- A path the ntuple lacks makes only its own `anyOf` alternative keep no events, and the pass goes on. So a misspelled path in one alternative shows up only as that alternative's count in the cutflow note, and inside an inverted `anyOf` such as `leptonVeto` the veto quietly stops removing those events.
- An `anyOf` inside `requirements` lets different objects pass through different groups, and all of them count toward `min`. An `anyOf` cut with one object cut per alternative needs `min` objects passing a single alternative, so the two give the same result only when `min` is 1.
- Kamui keeps every DV, even those outside the beampipe or with a broken covariance. A DV cut of your own needs `tightDV`, or both an `insideBeampipe` requirement and a `dBVErr` bound, or it counts DVs JMTucker never had.
- The two-DV regions can overlap, like JMTucker's: an event with tight DVs of 5, 6 and 4 tracks is in both `dv4x5` and `dv5x5`.
- Like JMTucker, `dv3x5` drops events that also hold a tight DV with 4 tracks, so it never shares an event with `dv4x5`.
- `dv3x5` and `dv4x5` copy JMTucker's bug of counting only DVs with exactly 5 tracks, so an event whose tight DVs have 3 and 6 tracks, or 4 and 6, lands in no two-DV region. See `Bugs/fiveTrackCappedAtFive.md`.

**Every Run 2 selection**
- These must keep matching JMTucker: any change has to reproduce JMTucker's yields again.

**run2/displaced.json**
- `leptonVeto` is `lepton.json`'s `leptonPlateau` inverted. Both name the `plateauMuon` and `plateauElectron` definitions, so their object cuts always match. Their trigger lists are written out in both files, so the channels stay disjoint only while you keep those lists the same.

**run2/lepton.json**
- Carries no orthogonality veto of its own, because in JMTucker the veto is only used in the displacement channel.
