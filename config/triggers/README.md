# Trigger Configs

One JSON file per trigger channel. A channel is the set of HLT paths that define one way of selecting events.

| File | Channel |
|---|---|
| `run2Displaced.json` | Run 2 b-jet and displaced-dijet paths, the displacement-triggered channel |
| `run2Lepton.json` | Run 2 single-electron and single-muon paths, the lepton-triggered channel |

## Fields

| Key | Meaning |
|---|---|
| `paths` | The HLT path patterns. Required. A trailing `_v*` matches any version of the path |
| `process` | The process name the trigger bits were written under. Defaults to `HLT` |
| `mode` | `any` for an OR over `paths`, `all` for an AND. Defaults to `any` |
| `_pathsByEra` | Optional. Which paths belong to which era's menu. Underscore keys are stripped at load, so this is documentation only |
## Referenced From Two Places
A content preset's `skim` block filters at production time. Ex: `config/content/run2/presets/dvLepton.json` says

```json
"skim": {"triggers": "run2Lepton"}
```


A selection config's cut filters at selection time. Ex: `config/selections/run2Displaced.json` says

```json
{"name": "trigger", "type": "trigger", "triggers": "run2Displaced"}
```

