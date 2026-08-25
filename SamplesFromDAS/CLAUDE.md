# SamplesFromDAS

Agent context for this directory. DAS catalog to condor/CRAB jobs to flat ntuples on EOS. Human-facing docs are ../README.txt and the planning documents in ../docs/.

## Layout

Sample processing: turning a DAS dataset into flat ntuples on EOS. The code that does it lives in the `python/kamui/` package, not here - see `python/kamui/CLAUDE.md`. This directory holds what is specific to this stage. `config/` has `samples/`, `content/`, `triggers/` and `sites.json`. `cmssw/` holds the three things that run inside CMSSW: `kamuiNtuple_cfg.py` (wiring only, no content decisions), `kamuiTables.py` (resolved JSON to table producers) and `inspectMiniAOD.py`. `tools/triggerYields.py` computes the DVCode comparison numbers. `jobs/` holds generated job areas and is gitignored, as is `branchDumps/`, which holds saved `edmDumpEventContent` output kept purely as reference for what a MiniAOD file contains.

## Content config

A collection names a MiniAOD product and a list of variables:

```json
"Jet": {"type": "patJet", "src": "slimmedJetsPuppi", "cut": "pt > 20", "maxLen": 40,
        "variables": {"pt": {"expr": "pt", "type": "float", "doc": "...", "precision": 10}}}
```

`type` is physics-facing (patJet, patMuon, vertex, secondaryVertex, packedCandidate, genParticle, global, pileup, genWeight and so on) and `content.py` maps it to the CMSSW plugin. `expr` is any const method of the C++ class, with `?:` ternaries and arithmetic. `precision` is retained mantissa bits and is the main storage knob — 10 bits is about 0.1% relative, plenty for pt/eta/phi. `mcOnly: true` makes a collection disappear automatically when the same preset is resolved for data. Presets compose with `include`. `run`, `luminosityBlock` and `event` are written automatically by the output module.

## Things that will bite

**Version skew.** Summer24 MiniAODv6 was written by CMSSW_15_0_2, so CMSSW_14_1_0_pre4 refuses to open it — "forward compatibility cannot be supported". Pinned at CMSSW_16_1_2 / el9_amd64_gcc13, set in `config/sites.json` under `cmssw`, which is what the condor jobs read. Recent rather than campaign-matched, but **do not bump it without asking Gianfranco** — a release change can introduce errors repo-wide.

**`electronID('name')` THROWS on an unknown name**, unlike `bDiscriminator()` which quietly returns -1000. The Winter22 IDs exist only in Run 3 and the Fall17 V2 IDs are what Run 2 needs, which is why `dvRun2Displaced` overrides them. Before switching campaign run `python3 cmssw/inspectMiniAOD.py <file>`, which lists the b-tag discriminators and lepton IDs actually embedded.

**Singleton plugins.** `SimpleBeamspotFlatTableProducer` and `SimpleGenEventFlatTableProducer` are `EventSingleton` types that reject a `singleton` parameter entirely. `content.py` flags them with `singletonImplicit` so `kamuiTables.py` knows to omit it.

**GenPart is stored with no cut on purpose** — `genPartIdxMother` indexes the source collection, so any cut silently corrupts the mother links. Prune upstream with a GenParticlePruner if it ever needs shrinking. **PV is stored with no maxLen on purpose** — capping it would also cap `nPV` and break pileup counting.

**Condor OS selection** uses `+DesiredOS = "EL9"`. If jobs sit idle forever try `+REQUIRED_OS = "rhel9"`. Not verified against a real submission. Each job also runs `scramv1 project` from cvmfs, roughly 30 s of startup; ship a tarball if job counts get large.

**Two EDM output modules in one CRAB task** (`--output both`) is not verified. If CRAB refuses, run two tasks.

## Run 3 jet ID reference

Kept here because `jets.json` deliberately stores raw energy fractions rather than a precomputed ID flag, so the working points are applied downstream and this table is what you apply. Run 3 TightLepVeto PF JetID (`RUN3CHSruns2022FGruns2023CD`), from [PFJetIDSelectionFunctor.h](https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/SelectorUtils/interface/PFJetIDSelectionFunctor.h):

| \|eta\| | NHF | NEF | CHF | CHM | nConst | MUF | CEF |
|---|---|---|---|---|---|---|---|
| ≤ 2.6 | < 0.99 | < 0.90 | > 0.01 | > 0 | > 1 | < 0.8 | < 0.8 |
| 2.6–2.7 | < 0.90 | < 0.99 | — | > 0 | > 1 | < 0.8 | < 0.8 |
| 2.7–3.0 | < 0.99 | < 0.99 | — | — | > 1 | — | — |
| > 3.0 (HF) | — | < 0.40 | — | — | nNeutral > 10 | — | — |

Changes from Run 2: NHF loosened from 0.9 to 0.99 in the barrel, and the CHF/CHM boundary moved from |eta| < 2.4 to < 2.6. Run 2 presets use CHS `slimmedJets` and therefore the Run 2 working points, not this table.

Two related gaps, both checked 2026-08: scouting jets have the energy-fraction variables on `Run3ScoutingPFJet` but no official JetID working point exists (the [Run3PFScouting twiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/Run3PFScouting) lists no criteria), and calo jets have no official Run 3 ID either.


## Measured numbers

Flat tree, Summer24 ggH mS55 ctau10mm, 4000 events, 2026-08-25. MiniAOD source is 67.5 kB/event.

| preset | kB/event | cmsRun 4k events |
|---|---|---|
| dvLight | 1.17 | 17 s |
| dvBase | 1.23 | 19 s |
| dvSignal | 2.11 | 28 s |
| dvFull | 6.49 | 52 s |

dvFull is dominated by the Track table, about 4.5 kB/event at pT > 1 GeV. The 716 HLT bit branches cost about 0.65 kB/event; drop them with `"keepAll": false` in core.json if a fixed path list is ever decided. The Run 2 presets add DVCode's pixel/strip layer cuts on top of pT > 1, which is the cut that makes the track table affordable.

Slimmed MiniAOD, same sample, 2000 events: 49 kB/event with the `tracks` group, only a 1.4x reduction. The branch breakdown says `packedPFCandidates` alone is 27 kB/event, so keeping tracks means keeping most of MiniAOD — that is inherent, not a bug in the keep list. Dropping the `tracks` group implies roughly 21 kB/event (derived from the branch breakdown, not measured directly).

## Verified working, 2026-08-25, CMSSW_16_1_2

All presets produce a readable flat Events tree with every expected branch. `isMC=False` correctly drops the four mcOnly collections. `GenPart_genPartIdxMother` and `GenPart_vx/vy/vz` (the LLP decay point) are present and filled. `Jet_btagUParTAK4B` is real in MiniAODv6 — mean -4.2, so only about 0.5% of jets hit the -1000 "tagger absent" sentinel, as expected for forward jets. Electron cut-based and MVA IDs read correctly in both Run 2 (Fall17 V2) and Run 3 (Winter22 V1). The HLT skim works: 193 of 716 paths fire in the Run 3 signal sample, and on a Run 2 ZH 2018 file the lepton-channel skim keeps exactly the 988 of 1768 events that pass the OR, verified three ways. `output=both` writes both files from one job. CRAB and condor job areas generate correctly under `--dry-run`, and phys03 samples get `inputDBS = 'phys03'` automatically.

## Discovered, not yet used

Run 3 MiniAOD carries collections Run 2 did not, all directly relevant to displaced vertexing and all currently unused: `displacedTracks` (a real `vector<reco::Track>` with full track parameters rather than packed ones), `slimmedDisplacedMuons`, `displacedStandAloneMuons`, `displacedGlobalMuons`, and `slimmedKshortVertices` / `slimmedLambdaVertices` (V0s, the main material-interaction background for DVs). They are in the slimmed-MiniAOD keep groups but have no flat-tree collections yet. Worth revisiting at milestone 3.

## Sample caveats from the Run 2 vs Run 3 survey, 2026-07

Exotic Higgs Run 3 has no generator filter, where Run 2 ggH had gen-HT > 200 GeV at about 8.2% efficiency, so Run 3 has roughly twice the raw events but around five times fewer useful ones. ZH and WH in Run 3 are V-inclusive where Run 2 were exclusive, leaving about 10% (Z to ll) or 30% (W to lnu) of events in the Run 2 leptonic phase space; Summer24 has exclusive ZH-Zto2L and WH-WtoLNu scan samples at 200k per point that are not yet in the catalog. RPV has nothing at all in Run 3 for gluino to tbs or stop to bb, and stop to dd exists only as a thin private brlopesd phys03 slice. Stealth SUSY is private, 2024 only, roughly 130 events per file, hence `nFilesFor10k = 100`.

## Glueballs — survey done 2026-08-25

Headline: **no dataset in CMS is called a glueball**, in either `prod/global` or `prod/phys03`. Neither is there anything under HiddenValley, TwinHiggs, FoldedSUSY or NeutralNaturalness in Run 3 (HV_ has 327 Run 2 datasets and zero Run 3). Searching for the word is a dead end — the physics ships under other banners. Two of those matter to us.

**HAHM, the Hidden Abelian Higgs Model, is the closest thing to a glueball sample in Run 3.** 128 Run 3 datasets, all five eras plus 21 in Summer24, named `HAHM-HTo2A-ATo2B-ATo2G_Par-M-*`. That is H to two scalars, each decaying to bb or gg, with the scalar mass scanned from 12 to 60 GeV. Both the topology and the mass range are what a Higgs-portal hidden glueball gives you, and the mass range straight-up covers our existing mS 15/40/55 grid. If glueballs enter scope, this is the family to look at first, not a new request.

**GluGluHToDarkShowers is much larger but is a different phenomenology.** 959 central Run 3 datasets across Summer22, 22EE, 23, 23BPix and 24, plus 168 private ones in Summer24, under scenario names ScenarioA, ScenarioB1, ScenarioB2, ScenarioC, HP and GluP. The scanned parameters are the dark pion mass mpi from 1 to 10 GeV, mA from 0.25 to 8 GeV, and ctau from 0.1 mm out to 100 m. That is a high-multiplicity shower of soft dark hadrons rather than one heavy long-lived scalar, so it is adjacent to us rather than ours. Worth knowing it exists and is enormous before anyone requests anything in this space.

One caveat with the same shape as our ggH filter problem: **288 of the 959 central dark shower datasets carry a PTH-80 filter** (Higgs pT above 80 GeV) and the other 671 do not, and none of the 168 private Summer24 ones do. Mixing filtered and unfiltered points without noticing would be an easy and expensive mistake, exactly as with the Run 2 versus Run 3 ggH gen-HT filter.

Also surveyed and less relevant: SUEP has 61 Run 3 datasets (`GluGluToSUEP_T*`, Summer22 through 23BPix, none seen in Summer24) but is soft and isotropic rather than displaced; DarkPhoton has 215 Run 3 datasets that are overwhelmingly monojet; and HToZdZd exists only in Run 2, with 87 datasets and no Run 3 equivalent.

Tentative conclusion for the sample plan: a dedicated glueball request is probably not needed. The HAHM Hto2A grid plus our existing Hto2Sto4B grid already covers the glueball-like topology and mass range. What is genuinely missing depends on whether we want the dark-shower high-multiplicity regime, and that is already covered centrally about as well as anything in this analysis.

Not checked: McM, for anything in production rather than on disk — it needs interactive auth. The DAS side is complete. Reproduce with `kamui find`, for example `./kamui find '/*HAHM*/*/MINIAODSIM'` or `./kamui find '/*GluGluHToDarkShowers*/*/MINIAODSIM' --instance prod/phys03`.

## nFilesFor10k

Files needed for about 10k events, measured 2026-07. Used only by `stage` and by `submit --backend condor --quick`; production submissions ignore it. Rough per-file event counts: ggH about 28k, StopStopbar about 10k, Stealth about 130, and ZH-2S-4D_mS55_ctau1mm anywhere from 20 to 5860 because those files are very uneven.
