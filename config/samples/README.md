# Sample Configs Documentation

Each JSON file here is a sample family: a set of datasets to process that belong together, such as one signal model. A sample is one DAS dataset with a short name, the era it belongs to, and the content preset its ntuples are written with. Commands such as `submit` work on the samples you pick by name, family, era or tag. A family lists its samples one by one, or generates them from a grid: name and dataset templates whose `{placeholders}` are filled in from lists of values called axes.
## JSON Fields

Below are all the supported fields one can add to the JSON file.

**Top level**

| Field | Meaning |
|---|---|
| `family` (optional, default: the file name) | The name for selecting this file's samples with `--family` |
| `defaults` (optional, default: None) | Sample fields applied to every sample in the file |
| `samples` (optional, default: None) | A list of explicit sample entries |
| `grids` (optional, default: None) | A list of grids, each generating samples from templates and axes |
| `overrides` (optional, default: None) | Fields to override on individual samples, keyed by sample name |

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
| **`name`** (required, default: None) | Short name for the sample, unique across every family. It also names the sample's output folder on EOS and its CRAB output dataset tag. |
| **`dataset`** (required, default: None) | The full DAS dataset path. |
| **`era`** (required, default: None) | Data-taking period. It picks the content folder the sample's preset comes from, `run2/` or `run3/`, and the selection thresholds the sample uses. |
| `dasInstance` (optional, default: `prod/global`) | `prod/global` for central datasets, `prod/phys03` for USER-created datasets. |
| `isMC` (optional, default: `true`) | `false` for data. `true` for MC. |
| `family` (optional, default: the file's `family` key, then the file name) | The name for selecting this file's samples with `--family`. |
| `content` (optional, default: `dvBase`) | The content preset defining the branches to write. |
| `tags` (optional, default: `[]`) | Free-form labels, for selecting samples with `--tag`. A sample may carry several. |
| `unitsPerJob` (optional, default: None) | A positive integer, the input files per job for this sample. `--filesPerJob` in the CLI overrides it. |
| `lumiMask` (optional, default: None) | A lumi mask JSON, such as the golden JSON, restricting processing to the lumi sections it lists. Data only. CRAB applies it and condor ignores it. |
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

A sample's fields come from four layers, each overriding the ones before it:

1. `defaults`
2. The grid's own fields, or the explicit sample entry
3. Any axis value whose key is also a sample field, such as `era` in the example
4. `overrides`

A later layer replaces lists and single values outright, so a grid that names `tags` throws away the `tags` in `defaults`.
## What Is Here Now

| File | What |
|---|---|
| `run3/exoticHiggs4d2024.json` | Summer24 Exotic Higgs H->SS->4d. Central |
| `run3/stealthSusy2024.json` | Summer24 Stealth SUSY SHH and SYY. Private |
| `run3/rpv2024.json` | Summer24 RPV stop->dd. Private |
| `run2/run2Validation.json` | Run 2 UL points for reproducing JMTucker results. Central |
| `run2/tutorial/zhLeptonTriggered.json` | The sample used in the tutorial slides. Central |

Each family file sits in the folder of its run, and Kamui stops with an error if a sample's era belongs to the other run. Family and sample names still carry their year or run, because commands pick samples by name across every folder.

## Relevant Commands

- Use `find` to get a dataset path from DAS before writing it here.
- Use `list` to confirm a family expanded into the samples you expected.
- Use `query` to ask DAS how many files, events and GB each registered sample holds.
- Use `stage` to copy MiniAOD files to EOS when you want to open one by hand.

See `python/kamui/README.md` for the flags and worked examples.

## Caveats

Physics caveats per family are kept here so the configs stay readable.

**Exotic Higgs (exoticHiggs4d2024)**
- Run 3 ggH has no gen-HT filter. The Run 2 samples had gen-HT > 200 GeV.
- ZH and WH decays are inclusive in Run 3. For Run 2 they are exclusive to lepton decays.
- Summer24 has exclusive ZH-Zto2L and WH-WtoLNu available. They have yet to be registered.

**RPV (rpv2024)**
- Private from Bruno. Nothing exists in Run 3 for gluino to tbs or stop to bb, official or private.

**Stealth SUSY (stealthSusy2024)**
- Private from Bruno.
- Each sample holds a single (mStop, mSo, ctau) point.
- Inclusive samples exist for Run 2. These can be filtered using `randPar`.

**Run 2 validation (run2Validation)**
- Dataset paths copied from JMTucker's `Tools/python/Samples.py`.
