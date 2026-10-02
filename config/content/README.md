# Content Documentation

These JSONs decide what ends up in your ntuples.

`collections/` describes what kind of object is worth storing, such as jets, and which of its variables to keep.

`presets/` combines those into a complete job configuration. Samples in `config/samples/` name one in their `content` field.

Two styles of configuration live here, split by what they decide:

- **Cut strings decide what gets stored:** A collection's `cut`, in the same CMSSW string language as `expr`.
- **Named fields decide physics:** Producer parameters such as `seeding` and `vertexing`, and everything in `config/selections/` and `config/definitions/`. A threshold named `min` or `max` includes its bound, and one named `above` or `below` excludes it.
## Layout
## Collections

A collection names one thing in MiniAOD and lists the variables to keep from it.

| Field | Meaning |
|---|---|
| **`type`** (required, default: None) | What kind of object it is. |
| **`src`** (required, default: None) | The MiniAOD collection it reads. |
| **`variables`** (required, default: None) | The branches to write. |
| `doc` (optional, default: `""`) | Written into the ROOT file as a descriptor. |
| `cut` (optional, default: `""`) | Only objects passing this are kept |
| `maxLen` (optional, default: None) | Keep at most this many |
| `singleton` (optional, default: `false`) | One object per event |
| `mcOnly` (optional, default: `false`) | The collection is dropped for data samples |
| `dataOnly` (optional, default: `false`) | The collection is dropped for MC samples |
| `seeding` (required for `seedTrack`, default: None) | The seed-track cuts |
| `jec` (required for `vertexJet`, default: None) | The JECs to re-apply |
| `requirements` (required for `vertexJet`, default: None) | The jets to keep, in the selection requirement syntax |
| `vertexing` (required for `dv`, default: None) | The vertexer parameters |

Four groups of `type` behave differently!

- `pileup` and `genWeight` have fixed content: their CMSSW producer decides the branches, so `variables` and `doc` are ignored. `pileup` reads its `src`. `genWeight` only records its `src` for reference, since its producer chooses its own input.
- `global` names EDM products directly, described below.
- `beamSpot` and `genEvent` always hold one object per event, so they ignore `singleton` and reject `cut` and `maxLen`.
- `vertexJet` writes nothing to the ntuple, so it rejects `variables`, `cut`, `maxLen` and `singleton`.

Each variable is a name and how to compute it:

```json
"pt": {"expr": "pt()", "type": "float", "doc": "Corrected pT [GeV]", "precision": 10}
```

| Field | Meaning |
|---|---|
| **`expr`** (required, default: None) | Any method of the underlying C++ object. Arithmetic and `?:` conditionals work |
| `type` (optional, default: `float`) | `float`, `double`, `int`, `uint`, `int16`, `uint16`, `uint8` or `bool` |
| `doc` (optional, default: `""`) | Written into the ROOT file as the branch description |
| `precision` (optional, default: None) | Floats only. Mantissa bits to keep, 0 to 32, or `-1` for full precision |

A `global` collection rejects `cut`, `maxLen` and `singleton`, and each of its variables names an EDM product with `src` in place of an `expr`:

| Field | Meaning |
|---|---|
| **`src`** (required, default: None) | The EDM product supplying the value |
| `type` (optional, default: `double`) | As above |
| `doc` (optional, default: `""`) | Written into the ROOT file as the branch description |

A `seedTrack` collection writes the DV seed tracks, and its `variables` are methods of `reco::Track`.

- The `seeding` block holds the seed cuts
  - `maxFirstPixelLayer` means a track's first barrel pixel hit must be in that layer or an inner one, or in layer 2 if no hit is missing before it.
- It has an optional `dxyErrScale`, MC only and keyed by era, that scales the dxy uncertainty in the `nSigmaDxyBsAbove` significance cut
  - `form` is one of `p0`, `p0-p2*exp(-p1*x)` or `p0-exp(-p1*x+p2)`, where `x` is the track pT.
- It has an optional `trackDrop` that is MC only: each track is dropped with probability `coefficient`*min(|dxy to the beamspot|, `absDxyBsCap`)^2, where `coefficient` is a number or an object keyed by era.
- It needs the `vertexing/` plugins built into the release.

A `vertexJet` collection produces the jets the vertexer's `sharedJets` step reads.

- The `jec` block names the payload, the primary vertices and the correction levels
- `requirements` chooses the jets using the `Jet` collection's variables, in the selection syntax of `config/selections/README.md`. It may name a definition from `config/definitions/`

A `dv` collection fits the DVs. Its `src` and its `vertexing.jets` name the collections it reads, and it takes no `cut`, `maxLen` or `singleton`.

- `kalman` holds the vertex fitter's settings, and `maxChi2PerDof` applies to every fit
- `sharedTracks`, `zRefit`, `mergeNearby` and `sharedJets` hold the thresholds of the four steps after seeding

See `vertexing/README.md` for what those steps do.

## Presets

A preset defines the collections you want to save in your output ntuples.

| Field | Meaning |
|---|---|
| `include` (optional, default: None) | Other collection or preset configs to build on |
| `collections` (optional, default: None) | Its own collections, overriding anything from the includes |
| `skim` (optional, default: None) | Keeps only events firing a trigger channel |
| `triggerBits` (optional, default: None) | Which HLT decision branches to write out |

A preset must end up with at least one collection, whether from `include` or its own `collections`.

**Under `skim`**

| Field | Meaning |
|---|---|
| `triggers` (optional, default: None) | Names a file in `config/triggers/`. Leaving it out means no skim, so every event is written |
| `mode` (optional, default: the trigger file's, then `any`) | `any` for an OR over the paths, `all` for an AND |
| `process` (optional, default: the trigger file's, then `HLT`) | The process the trigger bits were written under |

**Under `triggerBits`**

| Field | Meaning |
|---|---|
| **`processes`** (required, default: None) | The processes to keep decisions from: `HLT` for the triggers, and `PAT` or `RECO` for the `Flag_*` MET filters that selections read |

## What Is Here Now

Collections:

| Name | Holds |
|---|---|
| `core` | PVs, beamspot, PF and PUPPI MET, and rho. Also carries the file's `triggerBits` block |
| `jets` | AK4 jets, CHS for Run 2 and PUPPI for Run 3, plus uncorrected calo jets |
| `leptons` | Muons and electrons, with impact parameters and track reference points. Electron IDs are Fall17-94X-V2 for Run 2 and RunIIIWinter22-V1 for Run 3 |
| `vertices` | IVF secondary vertices from MiniAOD |
| `tracks` | Tracks and lost tracks, preselected to pT > 1 GeV with at least 2 pixel and 6 strip layers for the seed track definition |
| `gen` | Generator particles, generator MET, weights and pileup. All `mcOnly` |
| `vertexing` | DV seed tracks, the jets the `sharedJets` step reads, and the DVs |

- The `dxyErrScale` and `trackDrop` numbers come from the Run 2 analysis, which measured both by comparing data with MC. Run 3 has no such measurement yet, so the Run 3 seeding applies neither correction.
- `tightLepVeto`, the jet ID, has no Run 3 eras yet, so the Run 3 `VertexJet` uses only the pT and eta cuts of `analysisJet`.

Presets:

| Name | Era sets | What it is |
|---|---|---|
| `dvBase` | run2, run3 | `core`, `jets`, `leptons`, `vertices`  |
| `dvSignal` | run2, run3 | `dvBase` plus `gen` |
| `dvFull` | run2, run3 | `dvSignal` plus `tracks` |
| `dvDisplaced` | run2 | `dvFull` skimmed to the displacement-triggered channel |
| `dvLepton` | run2 | `dvFull` skimmed to the lepton-triggered channel |

## Relevant Commands

- Use `content` to see what a preset or collection resolves to.
- Use `stage` to copy MiniAOD files to EOS when you want to open one by hand.
- Run `check` after editing anything here.

See `python/kamui/README.md` for the flags and worked examples.

## Caveats

- `collections/` is searched before `presets/`, so the two cannot share a name.
- `expr` is C++ evaluated at job runtime, so `check` cannot catch a typo.
- Use `precision: -1` for anything a selection threshold compares against, including `vx`, `vy`, `vz` and the `PV` positions that impact parameters are recomputed from. Fewer bits can round pT onto a threshold and flip whether an object passes.
- `GenPart` takes no `cut` and `PV` no `maxLen`, since `genPartIdxMother` and `Track_pvIdx` point into them by position.
- `maxLen` keeps the first objects in `src` order, with no sorting. Jets arrive pT-ordered, `SV` does not.
