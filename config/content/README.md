# Content Configs

These decide what ends up in your ntuples.

`collections/` describes what kind of object is worth storing: variables corresponding to, e.g. jets, leptons, and tracks. 

`presets/` combines those into a complete job configuration. Samples in `config/samples/` name one in their `content` field.

## Layout

Content is split by era. Each set carries its own copy of every collection and its own presets. A sample never reaches across, so the same preset name resolves to a different file depending on which era asked for it.

## Collections

A collection names one thing in MiniAOD and lists the variables to keep from it.

| Field | Meaning |
|---|---|
| `type` | What kind of object it is |
| `src` | The MiniAOD collection it reads |
| `doc` | Written into the ROOT file as a descriptor |
| `cut` | Optional. Only objects passing this are kept |
| `maxLen` | Optional. Keep at most this many |
| `variables` | The branches to write |
| `singleton` | Optional. One object per event. |
| `mcOnly` | Optional. The collection disappears when the preset is resolved for data |
| `dataOnly` | Optional. The mirror of `mcOnly` |

Each variable is a name and how to compute it:

```json
"pt": {"expr": "pt()", "type": "float", "doc": "Corrected pT [GeV]", "precision": 10}
```

| Field | Meaning |
|---|---|
| `expr` | Any method of the underlying C++ object. Arithmetic and `?:` conditionals work |
| `type` | `float`, `double`, `int`, `uint`, `int16`, `uint16`, `uint8` or `bool` |
| `doc` | Written into the ROOT file as the branch description |
| `precision` | Optional, floats only. Mantissa bits to keep, 0 to 32, or `-1` for full precision |

A `global` collection is different: it has no `src`, no `cut` and no `maxLen`, and each of its variables names an EDM product with `src` in place of an `expr`.

## Presets

A preset is defines the collections you want to save in your output ntuples.

| Field | Meaning |
|---|---|
| `include` | Other collection or prest configs to build on |
| `collections` | Optional. Overrides anything the includes brought in |
| `skim` | Optional. `triggers` names a file in `config/triggers/`, and only events firing it are kept. |

Most presets are only an include list.

## What Is Here Now

Collections. Every one exists in both era sets, and `jets` and `leptons` differ between them.

| Name | Holds |
|---|---|
| `core` | PVs, beamspot, PF and PUPPI MET, rho, and the trigger bits |
| `jets` | AK4 jets, CHS for Run 2 and PUPPI for Run 3, plus uncorrected calo jets |
| `leptons` | Muons and electrons, with impact parameters and track reference points. Electron IDs are Fall17-94X-V2 for Run 2 and RunIIIWinter22-V1 for Run 3 |
| `vertices` | IVF secondary vertices from MiniAOD |
| `tracks` | Tracks and lost tracks, preselected to pT > 1 GeV with at least 2 pixel and 6 strip layers |
| `gen` | Generator particles, generator MET, weights and pileup. All `mcOnly` |

Presets:

| Name | Era sets | What it is |
|---|---|---|
| `dvBase` | run2, run3 | `core`, `jets`, `leptons`, `vertices`.  |
| `dvSignal` | run2, run3 | `dvBase` plus `gen`. The convention for MC families |
| `dvFull` | run2, run3 | `dvSignal` plus `tracks`.r |
| `dvDisplaced` | run2 | `dvFull` skimmed to the displacement-triggered channel |
| `dvLepton` | run2 | `dvFull` skimmed to the lepton-triggered channel |

## Relevant Commands

- Use `content` to see what a preset or collection resolves to.
- Use `stage` to copy MiniAOD files to EOS when you want to open one by hand.
- Run `check` after editing anything here.

See Kamui/python/kamui/README.md for the flags and worked examples.
