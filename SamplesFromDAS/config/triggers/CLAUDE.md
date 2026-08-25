# SamplesFromDAS/config/triggers

`README.txt` covers the fields and how a preset uses a channel. This is what to be careful about.

## Copied From JMTucker
- Copied from JMTucker `MFVNeutralino/python/TriggerFilter_cfi.py`.
    - `run2Displaced` is b-jet OR displaced-dijet, eleven paths. 
    - `run2Lepton` is single-electron OR single-muon, eight. 
    - Our Run 2 channels veto against the high-HT channel from EXO-19-013
    - JMTucker uses one path list for all four eras and relies on the filter not throwing, so a path missing from a year's menu never fires. We do the same. 

## The Offline Cuts Aren't Yet Applied
- Both channels reject events firing the HT > 1050 GeV trigger **and** having offline HT > 1200 GeV, for orthogonality to EXO-19-013. 
- The displacement channel additionally drops events firing a single-lepton trigger **and** passing the matching offline lepton selection, keeping it disjoint from the lepton channel. 
- The lepton channel has no such veto.
- Both require a trigger bit *and* an offline cut, which is why each `vetoes` entry carries an `offline` string.
- We apply neither yet. Every HLT bit and `Jet_pt` are stored, so both are reproducible downstream.

## The Veto in JMTucker
It lives in `plugins/AnalysisCuts.cc`: `apply_presel == 4` loops over `mfv::HTTriggers` and returns false on a match, `apply_presel == 6` does the same under `leptonht_veto`. It calls `satisfiesTrigger`, which pairs each trigger with its offline plateau, `ht(40) >= 1200 && njets >= 4` for `PFHT1050`. The groupings themselves are in `MFVNeutralinoFormats/interface/TriggerEnum.h`.
