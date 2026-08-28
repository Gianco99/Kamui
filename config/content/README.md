# Content Configs

These decide what ends up in your ntuples.

`collections/` describes what a single kind of object is worth keeping: which variables of a jet, a muon, a track. `presets/` combines those into a complete job configuration. You write a preset to define a new production, and a sample in `config/samples/` names one in its `content` field.

## Layout

Content is split by era. Each set carries its own copy of every collection and its own presets.

```
config/content/
  run2/  collections/  presets/
  run3/  collections/  presets/
```

An era picks the set: `2016`, `2016APV`, `2017` and `2018` read `run2/`, and everything else reads `run3/`. A sample never reaches across, so the same preset name resolves to a different file depending on which era asked for it.

## Collections

A collection names one thing in MiniAOD and lists the variables to keep from it.

| Field | Meaning |
|---|---|
| `type` | What kind of object it is: `patJet`, `patMuon`, `patElectron`, `patPhoton`, `patTau`, `patMET`, `packedCandidate`, `isolatedTrack`, `vertex`, `secondaryVertex`, `genParticle`, `candidate`, `beamSpot`, `genEvent`, `global`, `pileup`, `genWeight` |
| `src` | The MiniAOD collection it reads |
| `doc` | Written into the ROOT file as the table description |
| `cut` | Optional. Only objects passing this are kept |
| `maxLen` | Optional, 1 to 100000. Keep at most this many, in the order the source collection gives them |
| `variables` | The branches to write |
| `singleton` | Optional. One object per event, so `cut` and `maxLen` are refused |
| `extension` | Optional. Adds columns to a table another collection already declared |
| `params` | Only for `pileup` and `genWeight`, whose producers take no variables |
| `mcOnly` | Optional. The collection disappears when the preset is resolved for data |
| `dataOnly` | Optional. The mirror of `mcOnly` |
| `drop` | Optional, for an including config. Deletes a collection it inherited |

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

Fewer bits means a smaller file, and 10 bits is roughly 0.1 percent. Anything a selection threshold compares against is stored at `-1`.

A `global` collection is different: it has no `src`, no `cut` and no `maxLen`, and each of its variables names an EDM product with `src` in place of an `expr`.

## Presets

A preset is what you name when you submit.

| Field | Meaning |
|---|---|
| `include` | Other configs to build on, collections or presets |
| `collections` | Optional. Overrides anything the includes brought in |
| `skim` | Optional. `triggers` names a file in `config/triggers/`, and only events firing it are kept. `mode` and `process` override that file |

Most presets are only an include list.

## What Is Here Now

Collections, in both era sets:

| Name | Holds |
|---|---|
| `core` | Primary vertices, beamspot, PF and PUPPI MET, rho, and the trigger bits |
| `jets` | AK4 PUPPI jets, and uncorrected calo jets for the displaced-dijet trigger emulation |
| `leptons` | Muons and electrons, with impact parameters and track reference points |
| `vertices` | IVF secondary vertices from MiniAOD |
| `tracks` | Tracks and lost tracks, the input to offline vertexing. Much the largest table |
| `gen` | Generator particles, generator MET, weights and pileup. All `mcOnly` |

Presets:

| Name | Era sets | What it is |
|---|---|---|
| `dvBase` | run2, run3 | `core`, `jets`, `leptons`, `vertices`. Use for data |
| `dvSignal` | run2, run3 | `dvBase` plus `gen`. The convention for MC families |
| `dvFull` | run2, run3 | `dvSignal` plus `tracks`. Needed for offline vertexing, and much larger |
| `dvDisplaced` | run2 | `dvFull` matched to JMTucker: CHS jets and JMTucker's track preselection, skimmed to the displacement-triggered channel |
| `dvLepton` | run2 | `dvDisplaced` skimmed to the lepton-triggered channel |

## Using It

```bash
./kamui content                            # the presets each era set defines
./kamui content dvFull --era 2018          # what it resolves to, as MC
./kamui content dvFull --era 2018 --data   # the same preset, resolved for data
./kamui content dvFull --write out.json    # the resolved form a job receives
```

`--era` defaults to Summer24, which is a Run 3 era, so a Run 2 preset needs an explicit `--era 2018`. A collection name works anywhere a preset name does, which is the quickest way to see one table on its own.

Run `./kamui check` after editing anything here. It resolves every preset in both era sets, for MC and for data, confirms the two sets have not drifted apart, and confirms every sample asks for a preset its own era defines.
