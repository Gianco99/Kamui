# config/triggers

`README.txt` covers the fields and how a preset uses a channel. This is what to be careful about.

## Copied From JMTucker
- Copied from JMTucker `MFVNeutralino/python/TriggerFilter_cfi.py`.
    - `run2Displaced` is b-jet OR displaced-dijet.
    - `run2Lepton` is single-electron OR single-muon.
    - Our Run 2 channels veto against the high-HT channel from EXO-19-013
    - JMTucker uses one path list for all four eras and relies on the filter not throwing, so a path missing from a year's menu never fires. We do the same.

## The Offline Cuts Aren't Yet Applied
- Both channels reject events firing the HT > 1050 GeV trigger **and** having offline HT > 1200 GeV, for orthogonality to EXO-19-013.
- The displacement channel additionally drops events firing a single-lepton trigger **and** passing the matching offline lepton selection, keeping it disjoint from the lepton channel.
- The lepton channel has no such veto.
- Both require a trigger bit *and* an offline cut, which is why each `vetoes` entry carries an `offline` string.
- We apply neither yet. Every HLT bit and `Jet_pt` are stored, so both are reproducible downstream.

## Trigger Plateau Selections
Each channel pairs its triggers with an offline selection that puts the triggering object on the plateau. Recorded here rather than in the configs: a collection `cut` would delete objects from the ntuple instead of selecting events, and "at least one lepton passing" is an event-level requirement the content configs cannot express. Store the objects, cut downstream.

Lepton channel, from AN-21-201 Tables 17 and 18. At least one lepton must pass.

| | 2016APV | 2016 | 2017 | 2018 |
|---|---|---|---|---|
| muon pT | 27 | 27 | 30 | 27 |
| electron pT | 30 | 30 | 38 | 35 |

Both require `abs(eta) < 2.4`. Muons: medium cut-based ID, tight PF isolation, `abs(dxy)` wrt beamspot < 0.02 cm and `abs(dsz)` < 0.5 cm. Electrons: `cutBasedElectronID-Fall17-94X-V2-tight` with isolation folded into the ID, and `abs(dxy) < 0.05` / `abs(dsz) < 0.1` cm in the barrel, 0.1 / 0.2 cm in the endcap.

The 2017 muon threshold is 30, tracking the move to `IsoMu27`. That one is easy to miss.

Displacement channel: the AN says offline jet and b-tagging selections are applied but does not tabulate them the way it does for leptons, and each path carries its own requirement inside `AnalysisCuts.cc satisfiesTriggerAndOffline`. Read them from there.

## The Veto in JMTucker
It lives in `plugins/AnalysisCuts.cc`: `apply_presel == 4` loops over `mfv::HTTriggers` and returns false on a match, `apply_presel == 6` does the same under `leptonht_veto`. It calls `satisfiesTrigger`, which pairs each trigger with its offline plateau, `ht(40) >= 1200 && njets >= 4` for `PFHT1050`. The groupings themselves are in `MFVNeutralinoFormats/interface/TriggerEnum.h`.
