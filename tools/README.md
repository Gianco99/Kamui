# tools

Hand tools that read what the framework produced, or what it is about to consume. Nothing here is imported by `kamui`, and nothing here runs as part of a job.

## triggerYields.py

Counts, per sample, how many ntuple events fired a channel's HLT paths. It chains the sample's output files off EOS, evaluates the OR of the channel's trigger branches, and prints one line per sample. This is the number compared against JMTucker.

Needs `cmsenv` for ROOT. No grid proxy is needed for files already on our EOS.

```
python3 tools/triggerYields.py --task run2val
python3 tools/triggerYields.py --task run2val --sample rpvStopDD_M400_ctau1mm_2017 --perPath
python3 tools/triggerYields.py --files out.root --triggers run2Lepton
```

| Flag | Meaning |
| --- | --- |
| `--task` | Task name under `ntupleProduction/jobs/`. Samples and the EOS output directory come from that task's `task.json`; the channel comes from each sample's content preset. |
| `--files` | Ntuple files to read instead of a task. Requires `--triggers`. |
| `--triggers` | Name of a config in `config/triggers/`, e.g. `run2Lepton`. |
| `--sample` | Restrict a task to these samples. Repeatable. |
| `--perPath` | Also print how many events each individual path fired. |

### Reading the output

```
sample                                     channel            files     total      pass      eff
```

`channel` is the trigger config the sample's content preset skims on. `total` is the entries in the chained `Events` trees, `pass` the entries where at least one of the channel's paths is true, and `eff` their ratio in percent. Trigger branches are matched by stripping the version wildcard: `HLT_IsoMu24_v*` in the config is the branch `HLT_IsoMu24`.

Under `--perPath`, a path that has no branch in the chain prints `not in menu`, which is the normal state for a path belonging to another era's menu.

Lines outside the table report why a sample produced no number: it is no longer in the catalog, its content preset declares no trigger skim, its output directory on EOS is empty, or some of its files could not be opened or have no `Events` tree.

## inspectMiniAOD.py

Reports the b-tag discriminators, embedded lepton IDs, userFloats and userInts a MiniAOD file carries, each from the first event that has the collection. Run it before writing a content preset against a new campaign: a wrong electron ID name throws at job runtime and a wrong b-tag name quietly returns -1000, and both move between campaigns.

Needs `cmsenv` for FWLite. No grid proxy is needed for files already on our EOS.

```
python3 tools/inspectMiniAOD.py root://cmseos.fnal.gov//store/.../file.root
```

| Flag | Meaning |
| --- | --- |
| `--jets` | Jet collection to read. `slimmedJetsPuppi` by default, so a Run 2 file needs `--jets slimmedJets` |
| `--branches` | Also run `edmDumpEventContent` |
