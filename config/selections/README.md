# Selection Configs

A selection config is an ordered list of event-level cuts that `./kamui select` applies to production ntuples, writing out an ntuple with the same branches plus a cutflow. Cuts apply in the order they are listed, and that order is the cutflow order.

| File | Channel |
|---|---|
| `run2Lepton.json` | Run 2 lepton-triggered channel: single-electron or single-muon path, MET filters, one lepton on the plateau of the path that fired |
| `run2Displaced.json` | Run 2 displacement-triggered channel: b-jet or displaced-dijet path, high-HT veto, lepton-channel veto, per-path offline emulation, MET filters |

The era comes from each selected sample's catalog entry, and one copy of the selection is resolved per era present in the sample list.
## File Structure

Two top-level keys: 

- `eras`, a list of the eras this config is meant for.
-  `cuts`, the ordered cut list. 
## Cut Types

| `type` | Keeps an event when | Fields |
|---|---|---|
| `trigger` | Any of the named HLT paths fired | `triggers` |
| `flags` | Every named branch is true | `flags` |
| `quantity` | Every condition on a named event quantity holds | `conditions`, or inline `quantity` with `min` and `max` |
| `veto` | It did not both fire one of the named paths and meets every condition | `triggers` and `conditions` |
| `object` | At least one leg is satisfied | `anyOf` list of legs, or inline `collection`, `min`, `requirements` |
| `anyOf` | Every cut of at least one alternative passes | `anyOf` list of alternatives |

- `triggers` is either the name of a config in `config/triggers/`or an explicit list of path patterns. A pattern ending in `_v*` has that suffix stripped and is matched against the ntuple's branch names.

- `flags` is a list of branch names, all of which must be true.

- A `quantity` or `veto` cut names one of the quantities below and bounds it with `min` and `max`. Several conditions in one cut are ANDed.
  -  A `veto` pairs that with a trigger list and drops only the events that fired one of the paths and meet every condition, which is how orthogonality to another channel is implemented.

- An `anyOf` cut holds alternatives, each an object with `name`, `doc`, an optional `eras` list, and `cuts`. 
  - The cuts inside one alternative are ANDed, the alternatives are ORed, and an alternative whose `eras` does not include the era being run is dropped before anything is evaluated.

## Quantities

| Name | Meaning |
|---|---|
| `HT30`, `HT40` | Scalar pT sum over jets above 30 or 40 GeV with `abs(eta) < 2.5` passing the era's TightLepVeto ID |
| `nJet20`, `nJet40` | Count of those jets above 20 or 40 GeV |
| `caloHT30` | Scalar sum of raw calo-jet pT above 30 GeV with `abs(eta) < 2.5`, the quantity the displaced-dijet triggers cut on |
| `nCaloJet` | Size of the calo-jet collection |
| `nJet`, `nMuon`, `nElectron`, `nSV` | Collection sizes |
| `leadJetPt`, `leadMuonPt`, `leadElectronPt` | pT of the leading object, 0 for an empty collection |
| `MET` | `MET_pt` |

## Legs

A leg of an `object` cut asks how many objects of one collection satisfy every requirement.

| Key | Meaning |
|---|---|
| `collection` | Branch prefix, for example `Jet`, `Muon`, `CaloJet` |
| `min` | How many objects must satisfy the leg. A plain integer. Defaults to the length of `orderedMinPt`, or 1 |
| `requirements` | Per-object requirements, all ANDed |
| `orderedMinPt` | pT ladder in descending order: the k-th hardest surviving object must clear the k-th threshold |
| `pairRequirements` | Requirements on two surviving objects at once |
| `triggers` | Gates the leg on its own trigger |
| `doc` | Free text |

- A requirement names a `variable` and bounds it with `min`, `max`, `absMin` or `absMax`, the last two on the absolute value. It reads the branch `<collection>_<variable>`. Bounds are inclusive.
  - Ex: `{"variable": "pt", "min": 20}` on a `Jet` leg reads `Jet_pt`. 
- Listing the same variable twice stacks the bounds: the common object definition, then the path's own harder threshold.
- A requirement may instead be `{"anyOf": [[...], [...]]}`, requirement groups ORed per object. 
  - Ex: the electron impact-parameter cut either side of |eta| = 1.48.
- `pairRequirements` bound `absDiffMin` and `absDiffMax` on the separation between two objects that already passed, and hold when some pair works. 
  - Ex: `{"variable": "eta", "absDiffMax": 1.6}` is the dijet `MaxDeta1p6` leg, and needs `min` of at least 2.
- `triggers` gates the leg, so a muon leg counts only in events where a muon path fired.
- Legs within one `object` cut are ORed.

## Derived Per-Object Variables

Three variables are computed from other branches.

| Variable | Meaning |
|---|---|
| `tightLepVeto` | TightLepVeto PF jet ID for the era, applied to the `Jet` collection from the stored energy fractions. |
| `dxyBeamspot` | Track dxy with respect to the beamspot taken at the object's own z, following the beam tilt |
| `dzPV` | Track dz with respect to the PV, the first vertex passing `PV_isGood` |
## invert

`invert: true` on any cut keeps exactly the events that cut would otherwise have thrown away. Ex: how the displacement channel states its orthogonality to the lepton channel.
## Relevant Commands

- Use `select` to apply one of these to a production task's ntuples.
- Use `cutflow` to read what each cut kept afterwards.
- Run `check` after editing anything here.

See Kamui/python/kamui/README.md for the flags and worked examples.
