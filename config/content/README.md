# Content Documentation

These JSONs decide what ends up in your ntuples.

`collections/` describes what kind of object is worth storing: variables corresponding to, e.g. jets, leptons, and tracks. 

`presets/` combines those into a complete job configuration. Samples in `config/samples/` name one in their `content` field.

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
| `mcOnly` (optional, default: `false`) | The collection disappears when the preset is resolved for data |
| `dataOnly` (optional, default: `false`) | The mirror of `mcOnly` |

Three groups of `type` behave differently!

-  `pileup` and `genWeight` have fixed content: their CMSSW producer decides what branches to emit, so `variables` is unused,`doc` is dropped, and `src` is recorded as a papertrail while the producer sets its own.
- `global` names EDM products directly, described below.
-  `beamSpot` and `genEvent` hold one object per event by construction and reject `singleton`.

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

## Presets

A preset defines the collections you want to save in your output ntuples.

| Field | Meaning |
|---|---|
| `include` (optional, default: None) | Other collection or preset configs to build on |
| `collections` (optional, default: None) | Overrides anything the includes brought in |
| `skim` (optional, default: None) | Keeps only events firing a trigger channel |
| `triggerBits` (optional, default: None) | Which HLT decision branches to write out |

A preset must end up with at least one collection, whether from `include` or its own `collections`.

**Under `skim`**

| Field | Meaning |
|---|---|
| **`triggers`** (required, default: None) | Names a file in `config/triggers/` |
| `mode` (optional, default: the trigger file's, then `any`) | `any` for an OR over the paths, `all` for an AND |
| `process` (optional, default: the trigger file's, then `HLT`) | The process the trigger bits were written under |

**Under `triggerBits`**

| Field | Meaning |
|---|---|
| **`processes`** (required, default: None) | The processes to keep decisions from, e.g. `HLT`, `PAT`, `RECO` |

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

See Kamui/python/kamui/README.md for the flags and worked examples.
