# Sample Configs

A sample family is defined by a JSON file which declares a set of datasets to process. `configReaders/catalog.py` reads every `.json` file in this directory, and in any subdirectory of it, into one big sample catalog.

## Fields
| Field | Meaning |
|---|---|
| `name` | Short handle for the sample, unique across every family. It is also the per-sample output subdirectory on EOS and the CRAB output dataset tag, so it must start with a letter or digit and use only letters, digits, dot, dash and underscore. |
| `dataset` | The full DAS dataset path. |
| `dasInstance` | `prod/global` for central datasets (default), `prod/phys03` for USER-created ones. |
| `isMC` | True for simulation (default), false for data. |
| `era` | `Summer24`, `2018`, `2016APV`, etc.. Picks the content set the sample resolves against and the selection thresholds it is cut with. |
| `family` | The file the sample came from. Filled in automatically. |
| `content` | The content preset defining the branches to write, e.g. `dvSignal`. Defaults to `dvBase`. |
| `tags` | Free-form labels, used for selection. Defaults to empty. |
| `unitsPerJob` | A positive integer, the input files per job for this sample. The default is 5, and `--filesPerJob` overrides both. |
| `lumiMask` | Data only. Written into the CRAB config as `config.Data.lumiMask`. |
| `notes` | Anything a reader would want to know. |

Family and tag are two handles to select a group of samples. Family tells you which file the sample is written in (every sample has exactly one). Tag tells you what the sample is for (a sample can have multiple).

## Writing a Family File

A family lists samples one of two ways: explicitly under a `samples` key when there are only a few, or as a grid under a `grids` key when the datasets follow a pattern.

A grid is formed from templates and a list of axes. Every combination of the axes is generated, and each one fills in the `{placeholders}`. Example for two masses in one era:

```json
"name":    "rpvStopDD_M{mass}_ctau1mm_{era}",
"dataset": "/StopStopbarTo2Dbar2D_M-{mass}_CTau-1mm_TuneCP5_13TeV-pythia8/{campaign}/MINIAODSIM",
"axes": {
  "mass": ["400", "600"],
  "era":  [{"era": "2016APV", "campaign": "RunIISummer20UL16MiniAODAPVv2-106X_mcRun2_asymptotic_preVFP_v11-v2"}]
}
```

Write an axis as a plain list when each value fills in one placeholder of the same name, as `mass` does. Write it as a list of blocks when picking one value has to fill in several placeholders at once, as `era` does.

A grid may also carry any sample field and apply those to every point it generates. `skip` lists generated names to drop.

`defaults` applies to every sample in the file. `overrides` applies last and is where per-point exceptions go such as a different `unitsPerJob`.

Keys beginning with an underscore are comments and are stripped at every level on load, so you can annotate freely.
## What Is Here Now

| File | Samples | What |
|---|---|---|
| `exoticHiggs4d2024.json` | 54 | Summer24 Exotic Higgs H->SS->4d. Central, `dvSignal` |
| `stealthSusy2024.json` | 64 | Summer24 Stealth SUSY SHH and SYY. Private, `dvSignal` |
| `rpv2024.json` | 1 | Summer24 RPV stop->dd. One private point, `dvSignal`. |
| `run2Validation.json` | 24 | Run 2 UL points for reproducing JMTucker results. `dvDisplaced`and `dvLepton`. |
| `tutorial/zhLeptonTriggered.json` | 1 | The single sample followed end to end in the tutorial slides. `dvLepton`. |
## Querying the Sample Catalog

`./kamui list` allows the user to select samples registed here. The flags and worked examples are in Kamui/python/kamui/README.md.
