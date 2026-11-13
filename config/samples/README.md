# Samples

Each JSON file here is a sample family: a set of datasets to process that belong together, such as one signal model. A sample is one DAS dataset with a short name, the era it belongs to, and the content preset its ntuples are written with. Commands such as `submit` work on the samples you pick by name, family, era or tag.

A family lists a few samples one by one under `samples`, or generates them under `grids` when the datasets follow a pattern. A grid has name and dataset templates with `{placeholders}`, which Kamui fills in from lists of values called axes, once for every combination. A family with one sample listed by hand looks like this:

```json
{
  "family": "myFamily",
  "defaults": {"era": "<era>", "isMC": true, "content": "<preset>"},
  "samples": [{"name": "<sampleName>", "dataset": "<DAS dataset path>"}]
}
```

## JSON Fields

### Top Level

| Field | Meaning |
|---|---|
| `family` (optional) | The name for picking this file's samples with `--family`. Defaults to the file name |
| `defaults` (optional) | Sample fields applied to every sample in the file |
| `samples` (optional) | Explicit sample entries, as a list |
| `grids` (optional) | Grids, as a list, each generating samples from templates and axes |
| `overrides` (optional) | Fields to override on individual samples, keyed by sample name |

### Grid Level

| Field | Meaning |
|---|---|
| **`name`** (required) | Template for the sample name, with `{placeholders}` |
| **`dataset`** (required) | Template for the DAS path |
| `axes` (optional) | The values that fill the placeholders, as an object of non-empty lists. Every placeholder in `name` and `dataset` needs one |
| `skip` (optional) | Generated sample names to drop |

A grid may also carry any sample field from the table below, and applies it to every point it generates.

### Sample Level

| Field | Meaning |
|---|---|
| **`name`** (required) | A short name, unique across every family. It also names the sample's EOS output folder and CRAB output dataset tag |
| **`dataset`** (required) | The full DAS dataset path |
| **`era`** (required) | The data-taking period. It picks the content folder of the sample's preset, `run2/` or `run3/`, and its selection thresholds |
| `dasInstance` (optional, default `prod/global`) | `prod/global` for central datasets, `prod/phys03` for USER-created ones |
| **`isMC`** (required) | `true` for MC, `false` for data, without quotes |
| `family` (optional) | The name for picking this sample with `--family`. Defaults to the file's `family` key, then the file name |
| `content` (optional, default `dvBase`) | The content preset, which sets the branches written |
| `tags` (optional, default `[]`) | Free-form labels, as a list, for picking samples with `--tag` |
| `unitsPerJob` (optional) | Input files per job for this sample, a positive integer. `--filesPerJob` overrides it |
| `lumiMask` (optional) | A lumi mask JSON, as a path or URL, such as the golden JSON, that limits processing to the lumi sections it lists. Data only. Without it, jobs read every lumi section, certified or not |

## Writing a JSON Sample Family File

Each family file sits in the folder of its run, `run2/` or `run3/`. Commands pick samples by name across both folders, so family and sample names carry their year or run.

An example grid for two masses in one era:

```json
"name":    "rpvStopDD_M{mass}_ctau1mm_{era}",
"dataset": "/StopStopbarTo2Dbar2D_M-{mass}_CTau-1mm_TuneCP5_13TeV-pythia8/{campaign}/MINIAODSIM",
"content": "dvDisplaced",
"isMC":    true,
"axes": {
  "mass": ["400", "600"],
  "era":  [{"era": "2016APV", "campaign": "RunIISummer20UL16MiniAODAPVv2-106X_mcRun2_asymptotic_preVFP_v11-v2"}]
}
```

Write an axis as a plain list when each value fills in one placeholder of the same name, as `mass` does, and as a list of blocks when one value has to fill in several placeholders at once, as `era` does.

A sample's fields come from four layers, each overriding the ones before it:

1. `defaults`
2. The grid's own fields, or the explicit sample entry
3. Any axis value whose key is also a sample field, such as `era` in the example
4. `overrides`

A later layer replaces lists and single values outright, so a grid that names `tags` throws away the `tags` in `defaults`.

## What Is Here Now

| File | What it holds |
|---|---|
| `run3/exoticHiggs4d{2022,2022EE,2023,2023BPix,2024}.json` | Summer22 to Summer24 Exotic Higgs H->SS->4d. Central |
| `run3/exoticHiggs4b{2022,2022EE,2023,2023BPix,2024}.json` | Summer22 to Summer24 Exotic Higgs H->SS->4b. Central |
| `run3/exoticHiggs4tau{2022,2022EE,2023,2023BPix,2024}.json` | Summer22 to Summer24 Exotic Higgs H->SS->4tau, VBF only. Central |
| `run3/stealthSusy2024.json` | Summer24 Stealth SUSY SHH and SYY. Private, from Bruno |
| `run3/rpv2024.json` | Summer24 RPV stop->dd. Private, from Bruno |
| `run3/rpv4b2024.json` | Summer24 RPV stop->bb. Central |
| `run3/compressedStop{2022,2022EE,2023,2023BPix,2024}.json` | Summer22 to Summer24 long-lived stop with a compressed LSP. Central |
| `run2/run2Validation.json` | Run 2 UL points for reproducing JMTucker results. Central |
| `run2/tutorial/zhLeptonTriggered.json` | The sample used in the tutorial slides. Central |

Run 3 has no ggZH H->SS samples, so the ZH samples cover only the qq-initiated part.

## Relevant Commands

- `./kamui find` gets a dataset path from DAS, before you write it here.
- `./kamui list` confirms that a family expanded into the samples you expected.
- `./kamui query` asks DAS how many files, events and GB each registered sample holds.
- `./kamui stage` copies a sample's MiniAOD files to EOS, to run one job by hand on them.

The flags and worked examples are in `python/kamui/README.md`.

## Caveats

- `isMC` picks the global tag and the MC-only collections, and decides whether a blind selection may run on the sample. Kamui checks it against the dataset tier only for a central dataset, so get it right for a USER dataset.

### Exotic Higgs (`exoticHiggs4b*`, `exoticHiggs4d*` and `exoticHiggs4tau*` Families)

- Run 3 ggH has no gen-HT filter. The Run 2 ggH samples require gen-HT > 200 GeV.
- The `ggHPTH80` samples in 2022 and 2022EE are filtered on pTH > 80 GeV, so normalizing them needs that filter efficiency on top of the ggH cross section.
- ZH and WH decays are inclusive in Run 3, and exclusive to lepton decays in Run 2.
- The Summer24 exclusive ZH-Zto2L, WplusH-WtoLNu and GluGluZH datasets named `Hto2S` decay the Higgs promptly to a strange-quark pair, so they hold no LLP.

### Compressed Stop (`compressedStop*` Families)

- A generator filter requires MET > 100 GeV and HT > 200 GeV, so normalizing needs that filter efficiency.
