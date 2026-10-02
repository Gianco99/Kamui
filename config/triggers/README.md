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
| `include` (optional, default: None) | Another trigger config to build on. Naming `paths` replaces the inherited list |
| `mode` (optional, default: `any`) | `any` for an OR over `paths`, `all` for an AND |
| `process` (optional, default: `HLT`) | The process name the trigger bits were written under |

Kamui silently ignores unknown keys in a trigger config, so double-check spelling!
## Where These Are Used

A content preset's `skim` block names a trigger JSON by its file name, read from the run folder of the sample's era, and only events firing it reach the ntuple:

```json
"skim": {"triggers": "<trigger file name>"}
```

A selection's `trigger` cut can name one of these files as well. The Run 2 selections list their paths inline, so they do not follow edits made here.

## Caveats

- Path order inspired by JMTucker's, from `MFVNeutralino/python/TriggerFilter_cfi.py`.
- `mode` and `process` only affect the production skim. A selection cut reads just `paths`, so `mode: "all"` would mean AND in production but OR in selection.
