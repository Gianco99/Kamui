# config/content

`README.md` covers the two era sets, the two folders and the fields. This is what to be careful about.

## A Preset Is Resolved, Not Read
`resolveContent` flattens the `include` chain, drops `mcOnly` collections when `isMC` is false, drops `dataOnly` ones when it is true, maps each physics-facing `type` to its CMSSW plugin name, and expands `skim` from `config/triggers/`. What a job receives is the flattened result, which `./kamui content <name> --write` emits. Reading a preset file tells you almost nothing; run the command.

`--data` changes the answer, so every preset has to work both ways. `./kamui check` resolves every content config both ways for that reason.

A name in `include` is resolved against the era set's directory and then one level of subdirectories beneath it, in sorted order, so `collections/` is searched before `presets/`. A preset and a collection cannot share a name, and the collection would win.

`core.json` carries a top-level `triggerBits` block alongside `collections`, which stores every HLT bit. It is named `triggerBits` because `skim.triggers` in a preset means something else entirely, the name of a file in `config/triggers/`, and `resolveContent` returns both in one dict. Its `processes` list is `HLT`, `PAT` and `RECO` because the MET filter decisions are recomputed in PAT for MC and in RECO for data; a process absent from a file matches nothing.

## The Era Split Is A Wall
`contentDirs` returns exactly one directory, the era's own set, so a Run 2 sample can never resolve a Run 3 config or the reverse. `eraGroup` sends `2016`, `2016APV`, `2017` and `2018` to `run2` and everything else to `run3`. This exists because a MiniAOD accessor that names a thing the file does not carry fails at job runtime: `electronID('mvaEleID-RunIIIWinter22-iso-V1-wp90')` throws on a Run 2 file. Duplicating the collections was the price of never being able to point one at the wrong era.

`./kamui check` calls `validateEraCopies`, which reads both copies of each collection and compares the bytes. Every collection except `leptons` must be identical, and `leptons` must differ; `ERA_SPECIFIC_COLLECTIONS` in `configReaders/content.py` is the list. Editing `run2/collections/jets.json` alone therefore fails `./kamui check`. Copy the edit into `run3/` in the same commit. `leptons` differs only in the electron ID names, Fall17-94X-V2 for Run 2 and RunIIIWinter22-V1 for Run 3.

## expr Is C++, Evaluated By CMSSW
Each `expr` is a method call on the underlying object, parsed by CMSSW's string evaluator. Two consequences. A name that does not exist fails at job runtime, so `./kamui check` passes and a typo survives until a job dies on the grid. And the behavior on a missing quantity differs by accessor: `bDiscriminator()` returns -1000 for a tagger that is not there, while `electronID()` throws. `cmssw/inspectMiniAOD.py` exists to list what a given file actually carries.

## precision -1 Is Load-Bearing
`precision` truncates the mantissa, and a variable that a selection threshold compares against is stored at `-1`, full precision. Truncation quantises pT enough to push a sub-threshold object exactly onto a threshold, and a cutflow that has to reproduce JMTucker event for event cannot absorb that.

In `jets.json` that means `pt`, `eta` and `phi`, every energy fraction, `btagDeepFlavB`, and all four `CaloJet` variables. In `leptons.json` it means `pt`, `eta`, `phi`, `scEta`, the impact parameters, `sip3d`, the isolations, and `vx`, `vy`, `vz`. The track reference point is there because `select/engine.py` recomputes `dxyBeamspot` and `dzPV` from `vx`, `vy`, `vz` and the beamspot, so those three carry the precision of the cut. `PV_x`, `PV_y`, `PV_z`, `PV_ndof` and `PV_chi2` are at `-1` for the same reason.

Everything a threshold never sees is still a guess and was never derived from a resolution requirement. Track and vertex positions are worth setting deliberately, since displacement resolution is the measurement.

## Overrides Reach Inside, Except For Lists
A preset overriding a collection replaces only the keys it names, so `dvDisplaced` can change `Jet.src` without restating every jet variable. Lists replace wholesale. That is correct for `skim.hltPaths`, where `dvLepton` must swap 11 displacement paths for 8 lepton ones, where a merged list would give 19.

`dvDisplaced` also lists `"CaloJet": {}`. Merging an empty object changes nothing, since `CaloJet` already arrives from `jets`, and removing that line would not change what the preset resolves to.

## Notes On Individual Collections
`core` also supplies `run`, `luminosityBlock` and `event` without being asked: the output module writes them automatically. Its `Rho` collection uses the `global` type, which names an EDM product directly and never calls a method on an object, so it has no `src`.

`tracks` exists because MiniAOD has no `reco::Track`. Tracks live inside `pat::PackedCandidate`, split across `packedPFCandidates` for those attached to a PF candidate and `lostTracks` for those that are not. Displaced tracks frequently fail PF association and land in `lostTracks`, so a displaced-vertex analysis needs both. This is much the largest table, so its `cut` is the main storage lever.

`jets` stores raw energy fractions, so working points are applied downstream, in `select/quantities.py` with the table in `docs/JetID.txt`. Still open: AK8 jets if boosted topologies enter scope.

`CaloJet` reads `slimmedCaloJets` through the generic `candidate` type, with no `cut` and no jet energy correction, because the displaced-dijet triggers cut on raw calorimeter quantities and the offline emulation in `config/selections/run2Displaced.json` has to cut on the same thing. `nCaloJet` in that emulation is the stored multiplicity, which `maxLen` caps at 40; the emulation asks for at least 2, so the cap does not bite, and a requirement near 40 would be wrong. The collection is in every preset in both era sets, `run3` included, because `validateEraCopies` forces `jets.json` to stay identical.

`leptons` keeps muons and electrons down to pT > 5 GeV. The channel-defining lepton pT cut is a selection-stage decision and does not belong here. Electron ID names were checked against Summer24 MiniAODv6 with `cmssw/inspectMiniAOD.py` on 2026-08-25.

`vertices` holds the IVF secondary vertices from MiniAOD, which are a stand-in for the analysis object; the real displaced vertices need the refitting producer of milestone 4.

## Notes On Individual Presets
`dvDisplaced` overrides `dvFull` to match JMTucker: CHS `slimmedJets` for the jet collection, because that is what JMTucker selected on, and JMTucker's `mfvVertexTracks` preselection on both track collections, pT > 1 GeV with at least 2 pixel and 6 strip layers, read from `Vertexer_cfi.py` on 2026-08-25. That last one bakes a JMTucker choice into stored data, which is still an open decision. The Fall17 electron IDs used to be an override here and now come from `run2/collections/leptons.json`.

`dvLepton` is `dvDisplaced` with a different skim. JMTucker's offline lepton pT cut, muon 27 GeV or 30 in 2017 and electron 30, 38, 35 for 2016, 2017, 2018, is applied at the selection stage in `config/selections/run2Lepton.json`, which reproduces JMTucker event for event. Keeping it out of the content config is what lets both channels read the same ntuples and lets the threshold move without a reproduction.

## Two Collections Must Stay Uncut And Uncapped
`GenPart` has no `cut` because `genPartIdxMother` indexes the source collection and any cut renumbers the survivors, silently pointing every link at the wrong particle. `PV` has no `maxLen` for the same reason, since `Track_pvIdx` indexes it, and because capping would also cap `nPV` and break pileup counting. These read like oversights and are load-bearing: adding a cut or a cap produces no error, just wrong mothers and wrong vertex assignments.

`maxLen` truncates in source-collection order; nothing sorts the objects. Jets arrive pT-ordered so the cap takes the hardest; `SV` does not, so an event over the cap loses an arbitrary subset.

## Editing A Collection Changes Every Preset
Collections are shared. Adding a variable to `jets` adds it to every preset that includes it, in both era sets, and to every future production. That is the point, and it also means a change here is never local. Anything already produced is not comparable afterwards.
