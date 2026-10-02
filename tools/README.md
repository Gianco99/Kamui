# Tools

This folder holds standalone scripts that inspect the framework's inputs and outputs. Nothing here is imported by `kamui`, and nothing here runs as part of a job. Each script needs `cmsenv`.

## triggerYields.py

Counts, per sample, how many ntuple events fired at least one HLT path of a trigger channel, the set of paths in one `config/triggers/` file. This is the number compared against JMTucker.

```
python3 tools/triggerYields.py --task run2Val
python3 tools/triggerYields.py --task run2Val --sample rpvStopDD_M400_ctau1mm_2017 --perPath
python3 tools/triggerYields.py --files out.root --triggers run2/lepton
```

| Flag | Meaning |
| --- | --- |
| `--task NAME` (optional, default: None) | Task under `ntupleProduction/jobs/`. Samples and the EOS output directory come from its `task.json`, the channel from each sample's content preset |
| `--files FILE [FILE ...]` (optional, default: None) | Ntuple files to read. Overrides `--task`, and needs `--triggers` |
| `--triggers NAME` (optional, default: None) | A file in `config/triggers/`, named with its run folder, e.g. `run2/lepton`. Ignored under `--task` |
| `--sample NAME` (optional, default: None) | Restrict a task to these samples. Repeatable |
| `--perPath` (optional, default: None) | Also print how many events each individual path fired |

One of `--task` or `--files` is required.

The output columns are `sample channel files total pass eff`. Trigger branches are matched by stripping the version wildcard, so `HLT_IsoMu24_v*` in the config is the branch `HLT_IsoMu24`. Under `--perPath`, a path with no branch prints `not in menu`, which is normal for a path from another era's menu.

## inspectMiniAOD.py

Reports the b-tag discriminators, embedded electron IDs, userFloats and userInts a MiniAOD file carries, each from the first event that has the collection. Run it before writing a content preset for a new campaign, since electron ID and b-tag names change between campaigns: a wrong electron ID name crashes the job, and a wrong b-tag name quietly returns -1000.

```
python3 tools/inspectMiniAOD.py root://cmseos.fnal.gov//store/.../file.root
```

| Flag | Meaning |
| --- | --- |
| **`file`** (required, default: None) | Positional. A MiniAOD file, local path or xrootd URL |
| `--jets NAME` (optional, default: `slimmedJetsPuppi`) | Jet collection to read. A Run 2 file needs `--jets slimmedJets` |
| `--branches` (optional, default: None) | Also run `edmDumpEventContent` |

## Caveats

- `triggerYields.py`
    - The denominator is already skimmed. `--task` only counts samples whose content preset declares `skim.triggers`, so every event in the file passed the channel OR and `eff` lands at essentially 100%. The number is a consistency check that the stored bits agree with the skim the job applied. `--perPath` is the informative output: it shows which paths carry the channel and which are absent from the era's menu.
    - `mode` is ignored: the paths are always ORed, without a warning, even when a config says `mode: "all"`.
    - It reads the channel from the current configs and ignores the `resolvedContent` saved in `task.json`, so editing a preset after a task ran changes what this reports.
    - `--task` only finds files in the flat layout condor writes, one folder per sample. CRAB nests each sample's files several folders deeper, so `--task` finds nothing for a CRAB task. Use `--files` there.
- `inspectMiniAOD.py`
    - A collection is reported from the first event that has it. A signal sample can easily have no electrons in event 1, so reporting only event 1 would read as "these IDs are not embedded".
