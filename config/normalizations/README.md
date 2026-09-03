# Normalization Documentation

The numbers that turn a count of selected events into an expected yield.
## The Normalization Formula

```
N_expected = lumi[pb^-1] * xsec[pb] * filterEff * sum(per-event weights of passing events) / sumGenWeight
```
- `lumi` comes from `lumi.json`
- `xsec` and `filterEff` come from a cross section file, one per physics model
- `sumGenWeight` comes from `generatorSums.json`.
## Cross Section Files

One file per physics model, holding the cross sections its samples are normalized by.

**Top level**

| Field | Meaning |
|---|---|
| **`processes`** (required, default: None) | Cross section per production mode, keyed by process name |
| `filterEfficiencies` (optional, default: None) | Generator filter efficiency per sample family |

**Per process, under `processes`**

| Field | Meaning |
|---|---|
| **`xsec`** (required, default: None) | Cross section in picobarns |
| **`source`** (required, default: None) | Where the number came from |

**Per family, under `filterEfficiencies`**

| Field | Meaning |
|---|---|
| **`byScalarMass`** (required, default: None) | Efficiency keyed by the scalar mass |
| **`source`** (required, default: None) | Where the numbers came from |
## generatorSums.json

Written by the Kamui CLI command `norm`, with one entry per sample name under `samples`. Every field is optional because a sample keeps whatever `norm` has measured so far.

**Top level**

| Field | Meaning |
|---|---|
| **`samples`** (required, default: None) | The entries, keyed by sample name |

**Per sample, under `samples`**

| Field | Meaning |
|---|---|
| `genEvents` (optional, default: None) | Generated event count of the whole dataset |
| `sumGenWeight` (optional, default: None) | Sum of `genEventSumw`, the normalization denominator |
| `sumGenWeight2` (optional, default: None) | Sum of `genEventSumw2`, for the statistical uncertainty |

The current functionality reads everything from the run-level `Runs` tree written by the NanoAOD `genWeightsTable` producer. In the future this has to be adapted for other file formats.
## lumi.json

Integrated luminosity in inverse picobarns.

**Top level**

| Field | Meaning |
|---|---|
| **`eras`** (required, default: None) | Luminosity per era, keyed by name |
| `channels` (optional, default: None) | Per-channel overrides, keyed by channel then era |

**Per era, under `eras` and under a channel**

| Field | Meaning |
|---|---|
| **`lumi`** (required, default: None) | Integrated luminosity in pb^-1 |
| **`source`** (required, default: None) | Where the number came from |


Run 3 comes from the certified-golden luminosity:

-  `brilcalc totrecorded` with `-b 'STABLE BEAMS'` and `--normtag normtag_PHYSICS.json`, integrated over the official golden JSON for the era. 

Run 2 entries are taken from JMTucker `AnalysisConstants.h`.

`channels` holds the smaller luminosity a channel integrates when its triggers were not active for a whole era. 

-   Ex: `channels.displaced` overrides 2017 and 2018 for the displacement-triggered channel.

## Relevant Commands

- Use `norm` to register entries into `generatorSums.json`. 

See Kamui/python/kamui/README.md for the flags and worked examples.
