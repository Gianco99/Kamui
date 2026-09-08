# Tools

Hand tools that read what the framework produced, or what it is about to consume. Nothing here is imported by `kamui`, and nothing here runs as part of a job. Both need `cmsenv`.

## triggerYields.py

Counts, per sample, how many ntuple events fired a channel's HLT paths. This is the number compared against JMTucker.

```
python3 tools/triggerYields.py --task run2val
python3 tools/triggerYields.py --task run2val --sample rpvStopDD_M400_ctau1mm_2017 --perPath
python3 tools/triggerYields.py --files out.root --triggers run2Lepton
```

| Flag | Meaning |
| --- | --- |
| `--task NAME` (optional, default: None) | Task under `ntupleProduction/jobs/`. Samples and the EOS output directory come from its `task.json`, the channel from each sample's content preset |
| `--files FILE [FILE ...]` (optional, default: None) | Ntuple files to read instead of a task. Requires `--triggers`, and wins when both are given |
| `--triggers NAME` (optional, default: None) | A config in `config/triggers/`, e.g. `run2Lepton`. Ignored under `--task` |
| `--sample NAME` (optional, default: None) | Restrict a task to these samples. Repeatable |
| `--perPath` (optional, default: None) | Also print how many events each individual path fired |

One of `--task` or `--files` is required.

The table is `sample channel files total pass eff`. Trigger branches are matched by stripping the version wildcard, so `HLT_IsoMu24_v*` in the config is the branch `HLT_IsoMu24`. Under `--perPath`, a path with no branch prints `not in menu`, the normal state for another era's menu.

See `config/triggers/README.md` for the file format.

## inspectMiniAOD.py

Reports the b-tag discriminators, embedded electron IDs, userFloats and userInts a MiniAOD file carries, each from the first event that has the collection. Run it before writing a content preset against a new campaign: a wrong electron ID name throws at job runtime and a wrong b-tag name quietly returns -1000, and both move between campaigns.

```
python3 tools/inspectMiniAOD.py root://cmseos.fnal.gov//store/.../file.root
```

| Flag | Meaning |
| --- | --- |
| **`file`** (required, default: None) | Positional. A MiniAOD file, local path or xrootd URL |
| `--jets NAME` (optional, default: `slimmedJetsPuppi`) | Jet collection to read. A Run 2 file needs `--jets slimmedJets` |
| `--branches` (optional, default: None) | Also run `edmDumpEventContent` |

See `config/content/README.md` for what a preset does with these names.

