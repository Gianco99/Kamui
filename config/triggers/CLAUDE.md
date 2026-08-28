# config/triggers

`README.md` covers the fields and the two places a channel is referenced. This is what to be careful about.

## Copied From JMTucker

Both channels are transcribed from JMTucker `MFVNeutralino/python/TriggerFilter_cfi.py`. `run2Displaced` is `bjet_paths` followed by `displaced_dijet_paths`; `run2Lepton` is `electron_paths` followed by `muon_paths`. The order is JMTucker's, and keeping it makes a diff against that file readable. Do not sort them.

JMTucker hands one path list to all four eras and relies on `hltHighLevel` with `throw=False`, so a path absent from a year's menu simply never fires. Kamui does the same on both sides: `buildSkim` sets `throw=False`, and `triggerMask` in `select/engine.py` skips a pattern that matches no branch. The consequence to watch is asymmetric. A `trigger` cut whose patterns all match nothing returns an all-false mask and silently kills every event, while a `veto` cut in the same situation vetoes nothing at all. Both cases report `n/N paths present` in the cutflow note, which is the only place the mistake shows up.

## `vetoes` Is Declarative Only

`loadTriggerVetoes` exists and has no caller anywhere in the tree, and `_resolveSkim` does not look at `vetoes`. The vetoes that actually run are cuts in `config/selections/run2Displaced.json`, `htVeto` and `leptonVeto`, written with literal per-era path lists rather than by pointing back here.

Those selection cuts have since moved past the blocks in these files, so the blocks are not a specification to code against:

- `run2Displaced.json` names only `HLT_PFHT1050_v*` with an offline HT above 1200 GeV. The selection's `htVeto` also covers `HLT_PFHT800`, `HLT_PFHT900`, `HLT_PFJet450` and `HLT_AK8PFJet450` at HT40 above 1000 GeV for 2016APV and 2016, and adds `nJet20 >= 4`. That matches JMTucker, where `mfv::HTTriggers` holds all five paths and `satisfiesTrigger` requires `jet_ht(40) >= 1200 && njets(20) >= 4` for `PFHT1050`.
- `run2Lepton.json` declares an HT veto block, and `config/selections/run2Lepton.json` deliberately applies none. In JMTucker the orthogonality veto belongs to the displacement channel (`apply_presel == 6` under `leptonht_veto`), so the lepton channel keeps those events.

When a veto changes, the selection config is the file to edit. Update the block here only to keep the record honest.

## `mode` Reaches Only The Production Skim

`_resolveSkim` reads `mode` and `process` and validates `mode` against `any`/`all`; `loadTriggerPaths`, which is what a selection cut goes through, returns `paths` alone. A channel declaring `mode: "all"` would therefore be an AND in production and an OR in the selection, with nothing raising. Both current configs say `any`, so nothing diverges today. `tools/triggerYields.py` also always ORs.

## The Trigger Cut Duplicates The Skim

`dvLepton` skims on `run2Lepton` and `selections/run2Lepton.json` opens with a `trigger` cut on `run2Lepton`; the displacement channel pairs up the same way. The first cutflow line then passes essentially everything. That is intended. The cut order follows `AnalysisCuts.cc` so the two cutflows can be compared line by line, and stating the trigger explicitly also lets the same selection run over an unskimmed ntuple.

## Adding A Channel

The file name is the config name, and `loadWithIncludes` resolves it under `config/triggers/` or one level of subdirectories beneath it. `paths` is required: `loadTriggerPaths`, `_resolveSkim` and `validateTriggers` each complain when it is missing, and `./kamui check` runs `validateTriggers` over every file in this directory.

Trigger configs go through the same loader as every other config, so `include` works here. It deep-merges, and `deepMerge` replaces lists instead of extending them, so a config that includes another and restates `paths` overwrites the inherited list. Building a channel by including a neighbour and adding one path is not something this loader can express.

## Where The Offline Plateau Lives

A trigger config holds paths and nothing else. The offline selection that puts the triggering object on the plateau is an event-level requirement, and the content configs cannot state one: a collection `cut` deletes objects from the ntuple instead of selecting events. So the plateau requirements live in the selection configs, each leg gated on the path that fired it, and the ntuple simply stores the objects.

The lepton thresholds in `config/selections/run2Lepton.json` come from AN-21-201 Tables 17 and 18. The 2017 muon threshold is 30 GeV where the other years are 27, tracking the move to `IsoMu27`; that one is easy to miss when copying. For the displacement channel the AN does not tabulate the offline jet and b-tagging selections the way it does for leptons, and each path carries its own requirement inside `AnalysisCuts.cc satisfiesTrigger`. That is where the `displacedTriggerPresel` alternatives were read from.
