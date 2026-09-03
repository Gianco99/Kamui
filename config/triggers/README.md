# Trigger Documentation

One JSON file per trigger channel. A channel is the set of HLT paths that define one way of selecting events.

| File | Channel |
|---|---|
| `run2Displaced.json` | Run 2 b-jet and displaced-dijet paths, the displacement-triggered channel |
| `run2Lepton.json` | Run 2 single-electron and single-muon paths, the lepton-triggered channel |

## Fields

| Key | Meaning |
|---|---|
| **`paths`** (required, default: None) | The HLT path patterns. A trailing `_v*` matches any version of the path |
| `include` (optional, default: None) | Another trigger config to build on. Naming `paths` replaces the inherited list |
| `mode` (optional, default: `any`) | `any` for an OR over `paths`, `all` for an AND |
| `process` (optional, default: `HLT`) | The process name the trigger bits were written under |

 Nothing validates the key set of a trigger config, so double-check spelling!
## Where These Are Used

A content preset's `skim` block names a trigger JSON, and only events firing it reach the ntuple.  
Ex: `config/content/run2/presets/dvLepton.json` says

```json
"skim": {"triggers": "run2Lepton"}
```

Selection configs carry their trigger patterns inline rather than naming a config here.

