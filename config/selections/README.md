# Selection Documentation

A selection JSON is an ordered list of event-level cuts that `./kamui select` applies to production ntuples, writing out an ntuple with the same branches plus a cutflow. Cuts apply in the order they are listed, and that order is also the cutflow order.

| File | Channel |
|---|---|
| `run2Lepton.json` | Run 2 lepton-triggered channel: single-electron or single-muon path, MET filters, one lepton on the plateau of the path that fired |
| `run2Displaced.json` | Run 2 displacement-triggered channel: b-jet or displaced-dijet path, high-HT veto, lepton-channel veto, per-path offline emulation, MET filters |
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
| **`type`** (required, default: None) | One of the six below |
| `doc` (optional, default: `""`) | Free text, echoed into the cutflow |
| `invert` (optional, default: `false`) | Keeps exactly the events the cut would otherwise drop |
| `eras` (optional, default: None) | Read only on an `anyOf` alternative. Elsewhere it validates and does nothing |

## Cut Types

| `type` | Keeps an event when | Fields |
|---|---|---|
| `trigger` | Any of the named HLT paths fired | `triggers` |
| `flags` | Every named branch is true | `flags` |
| `quantity` | Every condition on a named event quantity holds | `conditions`, or inline `quantity` with `min` and `max` |
| `veto` | It did not both fire one of the named paths and meets every condition | `triggers` and `conditions` |
| `object` | At least one leg is satisfied | `anyOf` list of legs, or inline `collection`, `min`, `requirements` |
| `anyOf` | Every cut of at least one alternative passes | `anyOf` list of alternatives |

Some details regarding these cut types:

- `triggers` is the name of a config in `config/triggers/`, an explicit list of path patterns, or an object keyed by era holding either. 
  - A pattern ending in `_v*` has that suffix stripped and is matched against the ntuple's branch names.

- A `quantity` or `veto` names one of the quantities below. A `veto` is how orthogonality to another channel is implemented.

- An `anyOf` alternative needs only `cuts`; `name` defaults to `alternative <n>`, and `doc` and `eras` are optional.

## Quantities

These are derived quantities used for selections that do not come pre-packaged in the ntuples.

**Event level**:

| Name | Meaning |
|---|---|
| `HT30`, `HT40` | Scalar pT sum over jets above 30 or 40 GeV with `abs(eta) < 2.5` passing the era's TightLepVeto ID |
| `nJet20`, `nJet40` | Count of those jets above 20 or 40 GeV |
| `caloHT30` | Scalar sum of raw calo-jet pT above 30 GeV with `abs(eta) < 2.5` |
| `nCaloJet` | Size of the calo-jet collection |
| `nJet`, `nMuon`, `nElectron`, `nSV` | Collection sizes |
| `leadJetPt`, `leadMuonPt`, `leadElectronPt` | pT of the leading object, 0 for an empty collection |
| `MET` | `MET` transverse momentum |

**Object level**:

| Name | Meaning |
|---|---|
| `tightLepVeto` | TightLepVeto PF jet ID for the era, applied to the `Jet` collection from the stored energy fractions |
| `dxyBeamspot` | Track dxy with respect to the beamspot taken at the object's own z, following the beam tilt |
| `dzPV` | Track dz with respect to the PV, the first vertex passing `PV_isGood` |

## Legs

A leg of an `object` cut asks how many objects of one collection satisfy every requirement.

| Key | Meaning |
|---|---|
| **`collection`** (required, default: None) | Branch prefix, for example `Jet`, `Muon`, `CaloJet` |
| **`requirements`** (required, default: None) | Per-object requirements, all ANDed |
| `min` (optional, default: the length of `orderedMinPt`, or 1) | How many objects must satisfy the leg. A plain integer |
| `orderedMinPt` (optional, default: None) | pT ladder in descending order: the k-th hardest surviving object must clear the k-th threshold |
| `pairRequirements` (optional, default: None) | Requirements on two surviving objects at once |
| `triggers` (optional, default: None) | Gates the leg on its own trigger |
| `doc` (optional, default: `""`) | Free text |

- A requirement names a `variable` and bounds it with `min`, `max`, `absMin` or `absMax`.
  -  It reads the branch `<collection>_<variable>`, and bounds are inclusive.
- Listing the same variable twice stacks the bounds: first the common object definition, then the path's own harder threshold.
- A requirement may instead be `{"anyOf": [[...], [...]]}`, requirement groups ORed per object.
- `pairRequirements` bound `absDiffMin` and `absDiffMax` on the separation between two objects that already passed, and hold when some pair works.

## Relevant Commands

- Use `select` to apply one of these to a production task's ntuples.
- Use `cutflow` to read what each cut kept afterwards.
- Run `check` after editing anything here.

See Kamui/python/kamui/README.md for the flags and worked examples.
