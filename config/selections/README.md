# Selection Configs

One JSON file per analysis channel. A selection config is an ordered list of event-level cuts that `./kamui select` applies to production ntuples, writing out an ntuple with the same branches plus a cutflow. Cuts apply in the order they are listed, and that order is the cutflow order.

| File | Channel |
|---|---|
| `run2Lepton.json` | Run 2 lepton-triggered channel: single-electron or single-muon path, MET filters, one lepton on the plateau of the path that fired |
| `run2Displaced.json` | Run 2 displacement-triggered channel: b-jet or displaced-dijet path, high-HT veto, lepton-channel veto, per-path offline emulation, MET filters |

## Running One

```
./kamui select --selection run2Displaced --task myPass --inputTask myProduction --family run2Validation
./kamui cutflow --task myPass
```

The era comes from each selected sample's catalog entry, and one copy of the selection is resolved per era present in the sample list, so a single pass over samples from several years applies each year's own thresholds. `--cutflow` additionally writes one ntuple per cut beside the output, named after the cut, and works on the local backend only.

## File Structure

Two top-level keys: `eras`, a list of the eras this config is meant for, and `cuts`, the ordered cut list. Running against an era outside `eras` is refused. Any key beginning with an underscore is a comment and is dropped when the file loads, at every depth, which is what `_doc` is.

Every cut carries `name` and `type`. `doc` is free text and is echoed into the cutflow. `invert` is described below. Everything else a cut may carry depends on its type.

## Cut Types

| `type` | Keeps an event when | Fields |
|---|---|---|
| `trigger` | any of the named HLT paths fired | `triggers` |
| `flags` | every named branch is true | `flags` |
| `quantity` | every condition on a named event quantity holds | `conditions`, or inline `quantity` with `min` and `max` |
| `veto` | it did not both fire one of the named paths and meet every condition | `triggers` and `conditions` |
| `object` | at least one leg is satisfied | `anyOf` list of legs, or inline `collection`, `min`, `requirements` |
| `anyOf` | every cut of at least one alternative passes | `anyOf` list of alternatives |

`triggers` is either the name of a config in `config/triggers/` (`"triggers": "run2Lepton"` pulls in that channel's whole path list) or an explicit list of path patterns. A pattern ending in `_v*` has that suffix stripped and is matched against the ntuple's branch names, so `HLT_IsoMu24_v*` finds the branch `HLT_IsoMu24`; any other wildcard is matched with shell globbing.

`flags` is a list of branch names, all of which must be true.

A `quantity` or `veto` cut names one of the quantities below and bounds it with `min` and `max`. Several conditions in one cut are ANDed. A `veto` pairs that with a trigger list and drops only the events that fired one of the paths and meet every condition, which is how orthogonality to another channel is stated.

An `anyOf` cut holds alternatives, each an object with `name`, `doc`, an optional `eras` list, and `cuts`, which is an ordinary cut list resolved exactly like the top-level one. The cuts inside one alternative are ANDed, the alternatives are ORed, and an alternative whose `eras` does not include the era being run is dropped before anything is evaluated. This is how a channel that accepts several triggers, each with its own offline emulation, is written down.

## Quantities

| Name | Meaning |
|---|---|
| `HT30`, `HT40` | Scalar pT sum over jets above 30 or 40 GeV with `abs(eta) < 2.5` passing the era's TightLepVeto ID |
| `nJet20`, `nJet40` | Count of those jets above 20 or 40 GeV |
| `caloHT30` | Scalar sum of raw calo-jet pT above 30 GeV with `abs(eta) < 2.5`, the quantity the displaced-dijet triggers cut on |
| `nCaloJet` | Size of the calo-jet collection, with no requirement applied |
| `nJet`, `nMuon`, `nElectron`, `nSV` | Collection sizes, with no requirement applied |
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

A requirement names a `variable` and bounds it with `min`, `max`, `absMin` or `absMax`, the last two applying to the absolute value. The variable is read from the branch `<collection>_<variable>`, so `{"variable": "pt", "min": 20}` on a `Jet` leg reads `Jet_pt`. Bounds are inclusive. Listing the same variable twice stacks the bounds, which is how a leg states the common object definition and then the path's own harder threshold.

`pairRequirements` bound `absDiffMin` and `absDiffMax` on the separation between two objects that already passed every per-object requirement, and are satisfied when some pair works. `{"variable": "eta", "absDiffMax": 1.6}` is the dijet `MaxDeta1p6` leg. A leg with a pair requirement must ask for at least two objects.

A leg's `triggers` gates it: the leg counts only in events where one of its own paths fired. That is what lets an object cut hold a muon leg and an electron leg and have the muon leg count only when a muon path fired.

Legs within one `object` cut are ORed.

## Derived Per-Object Variables

Three variables are computed from other branches.

| Variable | Meaning |
|---|---|
| `tightLepVeto` | TightLepVeto PF jet ID for the era, applied to the `Jet` collection from the stored energy fractions. `docs/JetID.txt` carries the table |
| `dxyBeamspot` | Track dxy with respect to the beamspot taken at the object's own z, following the beam tilt |
| `dzPV` | Track dz with respect to the primary vertex, the first vertex passing `PV_isGood` |

`tightLepVeto` is a boolean, so it is required with `"min": 1`. The impact parameters are rebuilt from the track reference point, so they need `<collection>_vx`, `_vy`, `_vz` alongside `_pt`, `_eta`, `_phi`, and they need the `BeamSpot_` and `PV_` branches in the file.

## Per-Era Thresholds

Any threshold may be written as a single number or as an object keyed by era: `min`, `max`, `absMin`, `absMax`, `absDiffMin`, `absDiffMax`, and each entry of an `orderedMinPt` ladder. Only the era actually being run has to appear, so a threshold inside an alternative gated to 2018 need only define 2018.

```json
{"variable": "pt", "min": {"2016APV": 30, "2016": 30, "2017": 38, "2018": 35}}
```

Trigger lists and flag lists take the same treatment, which is how a path that only existed in some years, or a MET filter that only existed from 2017, is handled.

## invert

`invert: true` on any cut keeps exactly the events that cut would otherwise have thrown away. It is how the displacement channel states its orthogonality to the lepton channel: the cut is the lepton channel's own object selection, verbatim, with `invert` on top, so an event that the lepton channel would claim is dropped here. The cutflow shows the cut as `NOT (...)`.
