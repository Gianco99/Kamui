# Trigger Documentation

Each JSON file here is one trigger channel: the set of HLT paths that define one way of selecting events. Ntuple production and selections can use these files to keep only the events that fired a channel's paths.

| File | Channel |
|---|---|
| `run2/displaced.json` | Run 2 b-jet and displaced-dijet paths, the displacement-triggered channel |
| `run2/lepton.json` | Run 2 single-electron and single-muon paths, the lepton-triggered channel |
| `run3/bParking.json` | Run 3 single-muon impact-parameter paths, the B parking channel |
| `run3/vbfParking.json` | Run 3 paths that fed the VBF parking datasets, the VBF parking channel |

## Fields

| Key | Meaning |
|---|---|
| **`paths`** (required, default: None) | The HLT path patterns, as one list for every era or as an object mapping each era to its list, such as `{"<era>": ["<path>_v*"]}`. A trailing `_v*` matches any version of the path |
| `include` (optional, default: None) | A list of trigger config names to build on. Naming `paths` replaces the inherited list, era by era when both are keyed by era |
| `mode` (optional, default: `any`) | `any` for an OR over `paths`, `all` for an AND |
| `process` (optional, default: `HLT`) | The process name the trigger bits were written under |

Kamui stops with an error on any other key, on a `paths` that is not a non-empty list of path patterns or an object of such lists, and on a `mode` other than `any` or `all`. Paths keyed by era are read with the sample's era, and an era the file does not list is an error, so a channel cannot run in an era where it never existed. `check` also fails on an era key that is not an era of the file's run.
## Where These Are Used

A content preset's `skim` block names a trigger JSON by its file name, read from the run folder of the sample's era, and only events firing it reach the ntuple:

```json
"skim": {"triggers": "<trigger file name>"}
```

A selection's `trigger` cut can name one of these files as well. The Run 2 selections list their paths inline, so they do not follow edits made here.

## Caveats

- Path order inspired by JMTucker's, from `MFVNeutralino/python/TriggerFilter_cfi.py`.
- A selection's `trigger` cut keeps an event when any of its paths fired, so it refuses a trigger file whose `mode` is `all`. `process` only affects the production skim.
- Keep `run2/lepton.json` and `run2/displaced.json` as plain lists, since they reproduce JMTucker's channels event for event.
- A Run 3 file lists for each era only the paths that ran unprescaled in that era's data, since MC applies no HLT prescale and a prescaled path would fire in every MC event that passes it.
- An era may list a path under its data name and under its MC menu's name as well, when the two differ, so the channel fires in both.
