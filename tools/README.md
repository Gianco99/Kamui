# Tools

This folder holds standalone scripts that inspect the framework's inputs and outputs. `kamui` imports nothing from here, and no job runs any of it. Each script needs `cmsenv`.

## triggerYields.py

Counts, for each sample, how many ntuple events pass a trigger channel, the set of paths in one `config/triggers/` file. The channel's `mode` decides how the paths combine: with `any` an event passes when at least one path fired, and with `all` only when every path fired. This is the number compared against JMTucker.

```
python3 tools/triggerYields.py --task run2Val
python3 tools/triggerYields.py --task run2Val --sample rpvStopDD_M400_ctau1mm_2017 --perPath
python3 tools/triggerYields.py --files out.root --triggers run2/lepton
```

| Flag | Meaning |
| --- | --- |
| `--task NAME` (optional) | A task under `ntupleProduction/jobs/`. The samples, the EOS output directory and each sample's trigger paths and `mode` come from its `task.json`, which saved the skim each job ran with |
| `--files FILE [FILE ...]` (optional) | Ntuple files to read. Overrides `--task`, and needs `--triggers` |
| `--triggers NAME` (optional) | A file in `config/triggers/`, named with its run folder, such as `run2/lepton`. Ignored under `--task` |
| `--era NAME` (optional) | The era whose paths to read from a trigger file keyed by era. `--files` needs it for such a file. Ignored under `--task` |
| `--sample NAME` (optional) | Restricts a task to these samples. Repeatable |
| `--perPath` (optional) | Also prints how many events each individual path fired |

You need one of `--task` or `--files`.

The output columns are `sample channel files total pass eff`. Trigger branches are matched by stripping the version wildcard, so `HLT_IsoMu24_v*` in the config is the branch `HLT_IsoMu24`. Under `--perPath`, a path with no branch prints `not in menu`, which is normal for a path from another era's menu.

## inspectMiniAOD.py

Reports the b-tag discriminators, embedded electron IDs, userFloats and userInts a MiniAOD file carries, each from the first event that has the collection. Run it before writing a content preset for a new campaign, since electron ID and b-tag names change between campaigns. A wrong electron ID name crashes the job, and a wrong b-tag name returns -1000 without any error.

```
python3 tools/inspectMiniAOD.py root://cmseos.fnal.gov//store/.../file.root
```

| Flag | Meaning |
| --- | --- |
| **`file`** (required) | Positional. A MiniAOD file, as a local path or an xrootd URL |
| `--jets NAME` (optional, default `slimmedJetsPuppi`) | The jet collection to read. A Run 2 file needs `--jets slimmedJets` |
| `--branches` (optional) | Also runs `edmDumpEventContent` |

## Caveats

- `triggerYields.py`
    - The denominator is already skimmed. `--task` only counts samples whose content preset declares `skim.triggers`, so every event in the file already passed the channel's trigger, and `eff` comes out at essentially 100%. The number is a consistency check that the stored trigger bits agree with the skim the job applied. `--perPath` is the informative output: it shows which paths carry the channel and which are missing from the era's menu.
    - Which paths exist is read from the first file of the sample, so with `mode: "all"` a path missing from that file's menu is left out of the AND. Check `--perPath` for paths marked `not in menu`.
- `inspectMiniAOD.py`
    - A collection is reported from the first event that has it. A signal sample can easily have no electrons in event 1, so a report from event 1 alone would look like "these IDs are not embedded".
