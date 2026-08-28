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
| `vetoes` | Optional. Events the channel means to exclude, each entry a `paths` list plus an `offline` string naming the requirement that must hold as well. Nothing in the framework reads this; the vetoes actually in force are written out in `config/selections/run2Displaced.json` |

Any key beginning with an underscore is a comment and is dropped when the file loads, at every depth. `_doc` and `_pathsByEra` are both comments: `_pathsByEra` records which year's menu each path belonged to and has no effect on anything.

## Referenced From Two Places

A trigger config does nothing on its own. It is named by a string from two different kinds of file, and the two use it differently.

A content preset's `skim` block filters at production time. `config/content/run2/presets/dvLepton.json` says

```json
"skim": {"triggers": "run2Lepton"}
```

and the cmsRun job turns `paths`, `mode` and `process` into an `hltHighLevel` filter in front of the table producers, so events failing the OR never enter the ntuple at all.

A selection config's cut filters at selection time. `config/selections/run2Displaced.json` says

```json
{"name": "trigger", "type": "trigger", "triggers": "run2Displaced"}
```

and only `paths` is used: the selection engine ORs the patterns against the stored `HLT_*` branches and records the result as a cutflow line. `mode`, `process` and `vetoes` are ignored on this side. A `veto` cut and a single leg of an `object` cut carry a `triggers` key the same way, and all three places accept a literal list of path patterns in place of a config name.

The two references are independent. Naming a channel in a selection does not skim the ntuple, and skimming a production does not produce a cutflow line. Both Run 2 channels do both, with the same name on each side.

## Inspecting One

```
./kamui content dvLepton --era 2018
python3 tools/triggerYields.py --files out.root --triggers run2Lepton
```

The first prints the resolved `skim` block with the path list expanded. `--era` is needed because `kamui content` defaults to a Run 3 era while the Run 2 presets live in the Run 2 content set. The second counts how many events in a file pass the channel's OR, per path with `--perPath`. `./kamui check` confirms that every file here parses and declares `paths`.
