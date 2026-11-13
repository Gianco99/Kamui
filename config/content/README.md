# Content

The files here decide what a production job writes into your ntuples:

- A collection is one kind of MiniAOD object, such as jets, plus the variables to keep from it. Collection files sit in `collections/`.
- A preset picks the collections a job writes. Presets sit in `presets/`, and each sample in `config/samples/` names its preset in its `content` field.
- When you submit, Kamui merges the sample's preset and everything it includes into one resolved content JSON, the only config the job reads.

A preset can be one line:

```json
{"include": ["dvBase", "tracks"], "skim": {"triggers": "lepton"}}
```

It writes every collection in `dvBase` and `tracks`, and keeps only the events that fire the `lepton` trigger channel.

Two rules hold across these files:

- A collection's `cut` decides which objects get stored, in the same CMSSW string language as a variable's `expr`.
- Every setting that changes the physics results, such as `seeding` and `vertexing`, is a named JSON field, as is everything in `config/selections/` and `config/definitions/`. A threshold named `min` or `max` includes its bound, and one named `above` or `below` excludes it.

## Layout

`run2/` and `run3/` each hold their own copy of every collection, and their own presets. A sample reads its preset and everything it includes from the folder of its era, so a Run 3 sample never picks up a Run 2 file.

## Collections

| Field | Meaning |
|---|---|
| **`type`** (required) | What kind of object it is |
| `src` (required for every type except `global`, `pileup` and `genWeight`) | The MiniAOD collection it reads |
| `variables` (required for every type except `pileup`, `genWeight` and `vertexJet`) | The branches to write |
| `doc` (optional, default `""`) | The title of the `n<Name>` count branch in the ROOT file |
| `cut` (optional, default `""`) | Only objects passing this are kept |
| `maxLen` (optional) | The most objects to keep |
| `singleton` (optional, default `false`) | One object per event |
| `mcOnly` (optional, default `false`) | Drops the collection for data samples |
| `dataOnly` (optional, default `false`) | Drops the collection for MC samples |
| `seeding` (required for `seedTrack`) | The seed track cuts |
| `jec` (required for `vertexJet`) | The JECs to re-apply |
| `requirements` (required for `vertexJet`) | The jets to keep |
| `vertexing` (required for `dv`) | The vertexer parameters |

Each variable is a name and how to compute it:

```text
"pt": {"expr": "pt()", "type": "float", "doc": "Corrected pT [GeV]", "precision": <bits>}
```

| Field | Meaning |
|---|---|
| **`expr`** (required) | Any method of the underlying C++ object. Arithmetic and `?:` conditionals work |
| `type` (optional, default `float`) | `float`, `double`, `int`, `uint`, `int16`, `uint16`, `uint8` or `bool` |
| `doc` (optional, default `""`) | The branch description written into the ROOT file |
| `precision` (optional) | Floats only. The mantissa bits to keep, 0 to 32, or `-1` for full precision |

Each variable of a `global` collection names an EDM product with `src` in place of an `expr`:

| Field | Meaning |
|---|---|
| **`src`** (required) | The EDM product that supplies the value |
| `type` (optional, default `double`) | As above |
| `doc` (optional, default `""`) | As above |

A `seedTrack` collection writes the DV seed tracks, with `variables` that are methods of `reco::Track`, and needs the `vertexing/` plugins built into the release.

- `seeding` holds the seed cuts. `maxFirstPixelLayer` means a track's first barrel pixel hit must be in that layer or an inner one, or in layer 2 if no hit is missing before it.
- The optional `trackErrScale`, MC only and keyed by era, makes MC track uncertainties match data. The seed significance cut uses the corrected dxy uncertainty, and `DV_dBVErr` refits each DV with the corrected tracks.
  - Each era has a `barrel` and an `endcap` block, split at `barrelAbsEtaBelow`, each with a curve for `dxy`, `dsz` and their correlation `dxyDsz`.
  - A curve is a `form` in the track pT `x`, one of `p0`, `p0-p2*exp(-p1*x)`, `p0-exp(-p1*x+p2)` and `p0-p2*exp(-p1*x)+p3*x`, with its parameters in `p`.
- The optional `trackDrop`, MC only, drops each track with probability `coefficient`*min(|dxy to the beamspot|, `absDxyBsCap`)^2, where `coefficient` is a number or an object keyed by era.

A `vertexJet` collection makes the jets that the vertexer's `sharedJets` step reads, and writes no branches.

- `jec` names the payload, the primary vertices and the correction levels.
- `requirements` picks the jets by the `Jet` collection's variables, in the selection syntax of `config/selections/README.md`, and may name a definition from `config/definitions/`.

A `dv` collection fits the DVs. Its `src` and its `vertexing.jets` name the collections it reads.

- `kalman` holds the vertex fitter's settings, and `maxChi2PerDof` applies to every fit.
- `sharedTracks`, `zRefit`, `mergeNearby` and `sharedJets` hold the thresholds of the four steps after seeding, which `vertexing/README.md` explains.
- `beampipe` decides `DV_insideBeampipe`: a circle of `radius` around `dataCenter` in data, which moves by era, and around `mcCenter` in MC.

A `dvTrack` collection writes the tracks of every DV that the `dv` collection in its `src` keeps, one row per track with the index of its DV. Its `variables` are methods of `reco::Track`.

## Presets

| Field | Meaning |
|---|---|
| `include` (optional) | Collection or preset names to build on, as a list |
| `collections` (optional) | Its own collections, which override anything from the includes |
| `skim` (optional) | Keeps only the events that fire a trigger channel |
| `triggerBits` (optional) | Which HLT decision branches to write out |

### The `skim` Block

| Field | Meaning |
|---|---|
| `triggers` (optional) | A file in `config/triggers/`, from the folder of the sample's run. Without it, every event is written |
| `mode` (optional) | `any` for an OR over the paths, `all` for an AND. Defaults to the trigger file's `mode`, then `any` |
| `process` (optional) | The process the trigger bits were written under. Defaults to the trigger file's `process`, then `HLT` |

### The `triggerBits` Block

| Field | Meaning |
|---|---|
| **`processes`** (required) | The processes to keep decisions from, as a list: `HLT` for the triggers, and `PAT` or `RECO` for the `Flag_*` MET filters that selections read |

## What Is Here Now

### Collection Files

| Name | Holds |
|---|---|
| `core` | PVs, beamspot, PF and PUPPI MET, rho, and the `triggerBits` block |
| `jets` | AK4 jets, CHS for Run 2 and PUPPI for Run 3, plus uncorrected calo jets |
| `leptons` | Muons and electrons with their IDs, impact parameters and track reference points. The electron ID version differs by run |
| `vertices` | IVF secondary vertices from MiniAOD |
| `tracks` | Tracks and lost tracks, preselected with the pT cut and the minimum pixel and strip layers of the seed track definition |
| `gen` | Generator particles, generator MET, weights and pileup, all `mcOnly` |
| `vertexing` | DV seed tracks, the jets the `sharedJets` step reads, the DVs, and the tracks of each DV (Run 2 only) |

- The `trackErrScale` and `trackDrop` numbers are Run 2 measurements, made by comparing data with MC. Run 3 has no such measurement, so its seeding applies neither.
- Run 3 has no definitions, so the Run 3 `VertexJet` takes the pT and eta cuts of `analysisJet` without its jet ID, `tightLepVeto`.

### Preset Files

| Name | Era sets | What it is |
|---|---|---|
| `dvBase` | run2, run3 | `core`, `jets`, `leptons`, `vertices` |
| `dvSignal` | run2, run3 | `dvBase` plus `gen` |
| `dvFull` | run2, run3 | `dvSignal` plus `tracks`, and in Run 2 also `vertexing` |
| `dvDisplaced` | run2 | `dvFull` skimmed to the displacement-triggered channel |
| `dvLepton` | run2 | `dvFull` skimmed to the lepton-triggered channel |

## Relevant Commands

- `./kamui content` shows what a preset or collection resolves to and the branch names it writes.
- `./kamui stage` copies MiniAOD files to EOS, for prototyping a preset or running one job by hand.
- Run `./kamui check` after editing anything here.

The flags and worked examples are in `python/kamui/README.md`.

## Caveats

- CMSSW evaluates `expr` and `cut` when the job runs, so `check` can't catch a typo in them.
- Keep full precision, `precision: -1`, on any variable a selection cuts on or computes from, such as `vx`, `vy`, `vz` and the `PV` positions, since rounding can move a value across a threshold and flip whether an object passes. Every `dvTrack` variable needs full precision too, since a revertexer rebuilds each DV from them.
- Don't give `GenPart` or `PV` a `cut` or `maxLen`, since `genPartIdxMother` and `Track_pvIdx` point into them by position.
- `maxLen` keeps the first objects in `src` order without sorting. Jets arrive in pT order, and `SV` objects do not.
