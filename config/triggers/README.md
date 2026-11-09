# Trigger Documentation

Each JSON file here is one trigger channel: the set of HLT paths that define one way of selecting events. Ntuple production and selections can use these files to keep only the events that fired a channel's paths.

| File | Channel |
|---|---|
| `run2/displaced.json` | Run 2 b-jet and displaced-dijet paths, the displacement-triggered channel |
| `run2/lepton.json` | Run 2 single-electron and single-muon paths, the lepton-triggered channel |

## Fields

| Key | Meaning |
|---|---|
| **`paths`** (required, default: None) | The HLT path patterns. A trailing `_v*` matches any version of the path |
| `include` (optional, default: None) | A list of trigger config names to build on. Naming `paths` replaces the inherited list |
| `mode` (optional, default: `any`) | `any` for an OR over `paths`, `all` for an AND |
| `process` (optional, default: `HLT`) | The process name the trigger bits were written under |

Kamui stops with an error on any other key, on a `paths` that is not a non-empty list of path patterns, and on a `mode` other than `any` or `all`.
## Where These Are Used

A content preset's `skim` block names a trigger JSON by its file name, read from the run folder of the sample's era, and only events firing it reach the ntuple:

```json
"skim": {"triggers": "<trigger file name>"}
```

A selection's `trigger` cut can name one of these files as well. The Run 2 selections list their paths inline, so they do not follow edits made here.

## Caveats

- Path order inspired by JMTucker's, from `MFVNeutralino/python/TriggerFilter_cfi.py`.
- A selection's `trigger` cut keeps an event when any of its paths fired, so it refuses a trigger file whose `mode` is `all`. `process` only affects the production skim.
