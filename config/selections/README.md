# Selection Documentation

A selection JSON is an ordered list of event-level cuts, applied in the order they are listed. `./kamui select` runs one over the ntuples a `./kamui submit` task wrote, and writes out ntuples with the same branches holding only the events that pass. It also writes a cutflow: the number of events left after each cut, in the same order. Each cut has a `type`, such as `trigger` or `object`, that says what it checks.

| File | Channel |
|---|---|
| `run2/lepton.json` | Run 2 lepton-triggered channel: MET filters, then a single-muon or single-electron path that fired with one lepton on its plateau |
| `run2/displaced.json` | Run 2 displacement-triggered channel: high-HT veto, lepton-channel veto, a b-jet or displaced-dijet path that fired along with offline cuts that mimic it, MET filters |

Selections sit in a folder per run. A selection pass reads the file of that name from the run folder of each sample's era, so `--selection lepton` picks the Run 2 or Run 3 file to match the samples.
## File Structure

| Key | Meaning |
|---|---|
| **`cuts`** (required, default: None) | The ordered cut list |
| `eras` (optional, default: None) | The eras this config is meant for |
| `include` (optional, default: None) | Another selection config to build on. Naming `cuts` replaces the inherited list |

Any threshold, trigger list or flag list may be written as a single value or as an object keyed by era. Only the era being run has to appear.
## Cuts

Every cut carries these, whatever its type:

| Key | Meaning |
|---|---|
| **`name`** (required, default: None) | Names the cut, and its row in the cutflow |
| **`type`** (required, default: None) | One of the five below |
| `doc` (optional, default: `""`) | Free text, echoed into the cutflow |
| `invert` (optional, default: `false`) | Keeps exactly the events the cut would otherwise drop |
| `eras` (optional, default: None) | Used only on an `anyOf` alternative. Anywhere else it is accepted and ignored |

## Cut Types

| `type` | Keeps an event when | Fields |
|---|---|---|
| `trigger` | Any of the named HLT paths fired | `triggers` |
| `flags` | Every named branch is true, skipping any the ntuple lacks | `flags` |
| `quantity` | Every condition on an event quantity holds | `conditions`, or a single `quantity` with its bounds |
| `object` | Enough objects of one collection satisfy every requirement | `collection`, `requirements`, and the fields under Object Cuts |
| `anyOf` | At least one alternative passes all of its cuts | `anyOf` list of alternatives |

Some details regarding these cut types:

- `triggers` is the name of a config in the era's run folder of `config/triggers/`, an explicit list of path patterns, or an object keyed by era holding either. 
  - A pattern ending in `_v*` has that suffix stripped and is matched against the ntuple's branch names.

- A condition bounds one `quantity` with the same bounds a requirement uses, listed under Object Cuts. The `quantity` is an event branch, such as `MET_pt`, or a count or sum over a collection. `{"collection": "Jet", "requirements": [...]}` counts the objects passing the requirements, or every object when `requirements` is left out. Adding `"sum": "pt"` sums that variable over the same objects.

- An `anyOf` alternative needs only `cuts`; `name` defaults to `alternative <n>`, and `doc` and `eras` are optional.

- To keep a channel orthogonal to another, put the other channel's alternatives in an `anyOf` with `invert`, which drops every event the other channel would keep.

## Object Cuts

An `object` cut asks how many objects of one collection satisfy every requirement.

| Key | Meaning |
|---|---|
| **`collection`** (required, default: None) | Branch prefix, such as `Jet` |
| **`requirements`** (required, default: None) | Per-object requirements, all ANDed |
| `min` (optional, default: the length of `orderedMinPt`, or 1) | How many objects must satisfy the requirements. A plain integer |
| `orderedMinPt` (optional, default: None) | pT thresholds in descending order: the k-th highest-pT passing object needs pT at or above the k-th threshold |
| `pairRequirements` (optional, default: None) | Requirements on two surviving objects at once |

- A requirement names a `variable` and bounds it with `min`, `max`, `absMin` or `absMax`, which are inclusive, or `above`, `below`, `absAbove` or `absBelow`, which are exclusive.
  - It reads the branch `<collection>_<variable>`.
  - `dxyBeamspot` and `dzPV` are computed from the track reference point: dxy with respect to the beamspot at the object's own z, following the beam tilt, and dz with respect to the first PV passing `PV_isGood`.
- When the same variable appears twice, both bounds apply. This lets a cut name a shared definition and then add a harder threshold of its own, such as a higher pT for one trigger path.
- A requirement can also be `{"definition": "<name>"}`, which stands for the cuts of that definition in `config/definitions/`. It can also be `{"anyOf": [[...], [...]]}`, which an object passes when it passes every requirement in at least one group.
- `pairRequirements` bound how far apart two passing objects are in one `variable`, using `absDiffMin` and `absDiffMax`, and pass when at least one pair does.

## Relevant Commands

- Use `select` to apply one of these to a production task's ntuples.
- Use `cutflow` to read what each cut kept afterwards.
- Run `check` after editing anything here.

See `python/kamui/README.md` for the flags and worked examples.

## Caveats

- A trigger pattern matching no branch contributes nothing, so a `trigger` cut whose paths are all absent removes every event, and the channel with it. The cutflow's `0/N paths present` note is the only sign, and it is where a wrong era or a missing skim shows up.
- An `anyOf` inside `requirements` lets different objects pass through different groups, and all of them count toward `min`. An `anyOf` cut with one object cut per alternative needs `min` objects passing a single alternative, so the two give the same result only when `min` is 1.
- A DV selection has to apply JMTucker's beampipe veto before its yields can match JMTucker's. JMTucker keeps only vertices inside the beampipe, whose radius and center differ by era (`Tools/src/Geometry.cc`), and Kamui's DV collection keeps them all.
- JMTucker's vertex selector also drops every vertex whose fit covariance is not positive definite. Such a vertex gets a NaN uncertainty, and NaN fails every comparison in the selector, including the ones set to cut nothing. Kamui keeps these vertices.

**Both Run 2 configs**
- These must keep matching JMTucker: any change has to reproduce JMTucker's yields again.

**run2/displaced.json**
- `leptonVeto` is `lepton.json`'s `leptonPlateau` inverted. Both name the `plateauMuon` and `plateauElectron` definitions, so their object cuts always match. Their trigger lists are written out in both files, so the channels stay disjoint only while you keep those lists the same.

**run2/lepton.json**
- Carries no orthogonality veto of its own, because in JMTucker the veto is only used in the displacement channel.
