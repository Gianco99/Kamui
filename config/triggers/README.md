# Triggers

Each JSON file here is one trigger channel: the set of HLT paths that defines one way of selecting events. Ntuple production and selections can use these files to keep only the events that fired a channel's paths. The smallest file just lists its paths, and an event passes when any of them fired:

```json
{"paths": ["<pathA>_v*", "<pathB>_v*"]}
```

| File | Channel |
|---|---|
| `run2/displaced.json` | Run 2 b-jet and displaced-dijet paths, the displacement-triggered channel |
| `run2/lepton.json` | Run 2 single-electron and single-muon paths, the lepton-triggered channel |
| `run3/bParking.json` | Run 3 single-muon impact-parameter paths, the B parking channel |
| `run3/vbfParking.json` | Run 3 paths that fed the VBF parking datasets, the VBF parking channel |

## Fields

| Key | Meaning |
|---|---|
| **`paths`** (required) | The HLT path patterns, as one list for every era or as an object mapping each era to its list, such as `{"<era>": ["<path>_v*"]}`. A trailing `_v*` matches any version of the path |
| `include` (optional) | A list of trigger config names to build on. Naming `paths` replaces the inherited list, era by era when both are keyed by era |
| `mode` (optional, default `any`) | `any` for an OR over `paths`, `all` for an AND |
| `process` (optional, default `HLT`) | The process name the trigger bits were written under |

`paths` must be a non-empty list of path patterns or an object of such lists, and `mode` must be `any` or `all`. Kamui stops with an error otherwise, and on any key this table does not list.

When `paths` is keyed by era, Kamui reads the list for the sample's era. An era the file does not list is an error, so a channel can't run in an era where it never existed. `check` also fails on an era key that doesn't belong to the file's run.

## Where These Are Used

A content preset's `skim` block names a trigger file by its file name, and only the events that fire it reach the ntuple. Kamui reads the file from the run folder of the sample's era:

```json
"skim": {"triggers": "<trigger file name>"}
```

A selection's `trigger` cut can name one of these files too. The Run 2 selections write their paths out inline, so edits here don't reach them.

## Caveats

- The path order is modeled on JMTucker's, from `MFVNeutralino/python/TriggerFilter_cfi.py`.
- A selection's `trigger` cut keeps an event when any of its paths fired, so it refuses a trigger file whose `mode` is `all`. `process` only affects the production skim.
- Keep `run2/lepton.json` and `run2/displaced.json` as plain lists, since they reproduce JMTucker's channels event for event.
- A Run 3 file lists, for each era, only the paths that ran unprescaled in that era's data. MC applies no HLT prescale, so a prescaled path would fire in every MC event that passes it.
- When a path's name in data differs from its name in the MC menu, an era may list it under both names, so the channel fires in data and MC alike.
