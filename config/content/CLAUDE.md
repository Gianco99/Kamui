# config/content

`README.txt` covers the two folders and the fields. This is what to be careful about.

## A Preset Is Resolved, Not Read
`resolveContent` flattens the `include` chain, drops `mcOnly` collections when `isMC` is false, maps each physics-facing `type` to its CMSSW plugin name, and expands `skim` from `config/triggers/`. What a job receives is the flattened result, which `./kamui content <name> --write` emits. Reading a preset file tells you almost nothing; run the command.

`--data` changes the answer, so every preset has to work both ways. `./kamui check` resolves every content config both ways for that reason.

- `core.json` carries a top-level `triggerBits` block alongside `collections`, which stores every HLT bit. It is named `triggerBits` because `skim.triggers` in a preset means something else entirely, the name of a file in `config/triggers/`, and `resolveContent` returns both in one dict.

## expr Is C++, Evaluated By CMSSW
Each `expr` is a method call on the underlying object, parsed by CMSSW's string evaluator. Two consequences. A name that does not exist fails at job runtime, not at `./kamui check`, so a typo survives until a job dies on the grid. And the behavior on a missing quantity differs by accessor: `bDiscriminator()` returns -1000 for a tagger that is not there, while `electronID()` throws. That is why the Run 2 presets override the electron IDs, and why `cmssw/inspectMiniAOD.py` exists to list what a given file actually carries.

## precision Is A Guess
Values were never derived from a resolution requirement. It is the main storage lever and is worth setting deliberately, especially for track and vertex positions where displacement resolution is the measurement.

## Overrides Reach Inside, Except For Lists
A preset overriding a collection replaces only the keys it names, so `dvRun2Displaced` can change `Jet.src` without restating every jet variable. Lists replace wholesale. That is correct for `skim.hltPaths`, where `dvRun2Lepton` must swap 11 displacement paths for 8 lepton ones rather than getting 19, and it is a tax on `miniaod.keep`, which every preset restates in full.

## Notes On Individual Collections
`core` also supplies `run`, `luminosityBlock` and `event` without being asked: the output module writes them automatically. Its `Rho` collection uses the `global` type, which names an EDM product directly instead of calling a method on an object, so it has no `src`.

`tracks` exists because MiniAOD has no `reco::Track`. Tracks live inside `pat::PackedCandidate`, split across `packedPFCandidates` for those attached to a PF candidate and `lostTracks` for those that are not. Displaced tracks frequently fail PF association and land in `lostTracks`, so a displaced-vertex analysis needs both. This is much the largest table, so its `cut` is the main storage lever.

`jets` stores raw energy fractions, so working points are applied downstream. The Run 3 table is in `docs/JetID.txt`. Still open: AK8 jets if boosted topologies enter scope, and calo jets for the displaced-jet trigger study.

`leptons` electron ID names were checked against Summer24 MiniAODv6 with `cmssw/inspectMiniAOD.py` on 2026-08-25. `vertices` holds the IVF secondary vertices from MiniAOD, which are a stand-in rather than the analysis object; the real displaced vertices need the refitting producer of milestone 4.

## Notes On Individual Presets
`dvRun2Displaced` overrides `dvFull` to match JMTucker: CHS `slimmedJets` instead of PUPPI, because that is what JMTucker selected on; Fall17 electron IDs, because the Winter22 ones do not exist in Run 2 and `electronID()` throws; and JMTucker's `mfvVertexTracks` preselection on both track collections, pT > 1 GeV with at least 2 pixel and 6 strip layers, read from `Vertexer_cfi.py` on 2026-08-25. That last one bakes a JMTucker choice into stored data, which is still an open decision.

`dvRun2Lepton` is `dvRun2Displaced` with a different skim. JMTucker's lepton channel also applies an offline lepton pT cut, muon 27 GeV or 30 in 2017, electron 30, 38, 35 for 2016, 2017, 2018. Not applied here, by scope.

## Two Collections Must Stay Uncut And Uncapped
`GenPart` has no `cut` because `genPartIdxMother` indexes the source collection and any cut renumbers the survivors, silently pointing every link at the wrong particle. `PV` has no `maxLen` for the same reason, since `Track_pvIdx` indexes it, and because capping would also cap `nPV` and break pileup counting. These read like oversights and are load-bearing: adding a cut or a cap produces no error, just wrong mothers and wrong vertex assignments.

`maxLen` truncates in source-collection order; nothing sorts the objects. Jets arrive pT-ordered so the cap takes the hardest; `SV` does not, so an event over the cap loses an arbitrary subset.

## Editing A Collection Changes Every Preset
Collections are shared. Adding a variable to `jets` adds it to every preset that includes it, and to every future production. That is the point, and it also means a change here is never local. Anything already produced is not comparable afterwards.
