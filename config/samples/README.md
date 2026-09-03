# Sample Configs Documentation

A sample family is defined by a JSON file which declares a set of datasets to process.
## JSON Fields

Below are all the supported fields one can add to the JSON file. JSONs don't natively support comments, but you can add any arbitrary field with a leading `_` to make in-line notes. These fields are stripped when parsed to enable this functionality.

**Top level**

| Field | Meaning |
|---|---|
| `family` (optional, default: the file name) | The handle the samples in this JSON are selected by |
| `defaults` (optional, default: None) | Sample fields applied to every sample in the file |
| `samples` (optional, default: None) | A list of explicit sample entries |
| `grids` (optional, default: None) | A list of grids, each generating samples from templates and axes |
| `overrides` (optional, default: None) | Override defaults, keyed by generated sample name |

A file needs at least one of `samples` or `grids` to define samples.

**Grid level**

| Field | Meaning |
|---|---|
| **`name`** (required, default: None) | Template for the sample name, with `{placeholders}` |
| **`dataset`** (required, default: None) | Template for the DAS path |
| `axes` (optional, default: None) | The values substituted into the placeholders |
| `skip` (optional, default: None) | Generated sample names to drop |

A grid may also carry any sample field from the table below, applying it to every point it generates.

**Sample level**

| Field | Meaning |
|---|---|
| **`name`** (required, default: None) | Short handle for the sample, unique across every family. It is also the per-sample output subdirectory on EOS and the CRAB output dataset tag. |
| **`dataset`** (required, default: None) | The full DAS dataset path. |
| **`era`** (required, default: None) | Data-taking period. Picks the content set the sample resolves against and the selection thresholds it is cut with. |
| `dasInstance` (optional, default: `prod/global`) | `prod/global` for central datasets, `prod/phys03` for USER-created datasets. |
| `isMC` (optional, default: `true`) | `false` for data. `true` for MC. |
| `family` (optional, default: the file's `family` key, then the file name) | The handle the samples in this JSON are selected by. |
| `content` (optional, default: `dvBase`) | The content preset defining the branches to write. |
| `tags` (optional, default: `[]`) | Free-form labels, used for selection. A sample may carry several. |
| `unitsPerJob` (optional, default: None) | A positive integer, the input files per job for this sample. `--filesPerJob` in the CLI overrides it. |
| `lumiMask` (optional, default: None) | Mask certain lumi-blocks from being processed. Data only. |
## Writing a JSON Sample Family File

A family lists samples one of two ways: 

- Explicitly under a `samples` key when there are only a few.
- As a grid under a `grids` key when the datasets follow a pattern.

  - A grid is formed from templates and a list of axes. 
  - Every combination of the axes is generated, and each one fills in the `{placeholders}`.

Example grid for two masses in one era:

```json
"name":    "rpvStopDD_M{mass}_ctau1mm_{era}",
"dataset": "/StopStopbarTo2Dbar2D_M-{mass}_CTau-1mm_TuneCP5_13TeV-pythia8/{campaign}/MINIAODSIM",
"content": "dvDisplaced",
"axes": {
  "mass": ["400", "600"],
  "era":  [{"era": "2016APV", "campaign": "RunIISummer20UL16MiniAODAPVv2-106X_mcRun2_asymptotic_preVFP_v11-v2"}]
}
```

Write an axis as a plain list when each value fills in one placeholder of the same name, as `mass` does. Write it as a list of blocks when picking one value has to fill in several placeholders at once, as `era` does.

Four fields layer with increasing precedence, so that later fields override earlier definitions:

1. `defaults`
2. The grid's own fields, or the explicit sample entry
3. Any axis substitution whose key happens to be a sample field
4. `overrides`

Merging replaces lists and scalars; for example, a grid that names `tags` throws away the `tags` in `defaults`.
## What Is Here Now

| File | Samples | What |
|---|---|---|
| `exoticHiggs4d2024.json` | 54 | Summer24 Exotic Higgs H->SS->4d. Central |
| `stealthSusy2024.json` | 64 | Summer24 Stealth SUSY SHH and SYY. Private |
| `rpv2024.json` | 1 | Summer24 RPV stop->dd. Private |
| `run2Validation.json` | 24 | Run 2 UL points for reproducing JMTucker results. Central |
| `tutorial/zhLeptonTriggered.json` | 1 | A single sample used in the tutorial slides. Central |

## Relevant Commands

- Use `find` to get a dataset path from DAS before writing it here.
- Use `list` to confirm a family expanded into the samples you expected.
- Use `query` to ask DAS how many files, events and GB each registered sample holds.
- Use `stage` to copy MiniAOD files to EOS when you want to open one by hand.

See Kamui/python/kamui/README.md for the flags and worked examples.
