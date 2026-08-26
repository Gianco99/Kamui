# config/samples

`README.txt` here covers the fields, the two ways of writing a family, and what is currently in the catalog.
This file contains information on caveats to be wary about.

## Sample Caveats
Physics caveats per family are kept here so the configs stay readable.

**Exotic Higgs (exoticHiggs4d2024)**
- Run 3 ggH has no gen-HT filter, where the Run 2 samples had gen-HT > 200 GeV.
- ZH and WH are V-inclusive in Run 3 and were exclusive in Run 2.
- Summer24 does have exclusive ZH-Zto2L and WH-WtoLNu but they are not in the catalog yet.

**RPV (rpv2024).**
- One private point from Bruno. Nothing exists in Run 3 for gluino to tbs or stop to bb, official or private.

**Stealth SUSY (stealthSusy2024).**
- Private from Bruno.
- Exclusive per (mStop, mSo, ctau).

**Run 2 validation (run2Validation).**
- Dataset paths and event counts copied from DVCode's `JMTucker/Tools/python/Samples.py` on 2026-08-25.
- Procedure is in `docs/VALIDATION.txt`.

## Selection Values Are Checked and Matched
`--family`, `--era` and `--tag` are resolved case-insensitively against what exists in the catalog. A value matching nothing raises, naming every value that does exist.
- Tags are free-form in the config; the flag still has to match one that exists.
- `--name` is exact and case-sensitive as it refers to a specific sample name.
- `--match` is a wildcard glob that is meant to return nothing sometimes.

## Names Are Globally Unique
Names must be unique across the whole catalog. The name doubles as the output subdirectory, so a collision would put two samples' ROOT files in the same place.

## Filtering on Grid Axes
A grid writes many samples from one template, substituting every combination of its axes. For example, this one gives eight, two masses times four eras:

```
  "name":    "rpvStopDD_M{mass}_ctau1mm_{era}",
  "dataset": "/StopStopbarTo2Dbar2D_M-{mass}_CTau-1mm_.../{campaign}/MINIAODSIM",
  "axes": {
    "mass": ["400", "600"],
    "era":  [{"era": "2016APV", "campaign": "RunIISummer20UL16MiniAODAPVv2-..."}, ...]
  }
```

The selection flags are a fixed list: only `--name`, `--family`, `--era`, `--tag` and `--match` exist.
- `--era 2018` works because there is an `--era` flag and the axis called `era` fills the sample's `era` field.
- There is no `--mass` flag, so that axis only ever fills in the template; select those with `--match 'rpvStopDD_M400*'`.
- Name an axis after a field and it feeds that flag, otherwise it does not.

Where a field is set twice, the later setting wins:
- `defaults` first
- Then the grid or sample entry.
- Finally `overrides`.

## What Check Cannot Tell You
`./kamui check` only catches malformed JSON, bad field names, missing content presets, duplicate names and misshapen dataset paths. It cannot tell you whether a dataset actually exists. `./kamui query` asks DAS, and needs a proxy.
