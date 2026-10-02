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

One file per physics model, holding the cross sections its samples are normalized by. Its top level holds one block per run, `run2` or `run3`, and a sample is normalized with the block of its era's run.

**Per run, under `run2` or `run3`**

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

`norm` reads these numbers from the `Runs` tree of the sample's NanoAOD, where the NanoAOD `genWeightsTable` producer writes them. Any other file format would need its own reader.
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

- `totrecorded` from `brilcalc lumi` with `-b 'STABLE BEAMS'` and `--normtag normtag_PHYSICS.json`, integrated over the official golden JSON for the era.

Run 2 entries are taken from JMTucker `AnalysisConstants.h`.

`channels` holds the smaller luminosity a channel integrates when its triggers were not active for a whole era. 

-   Ex: `channels.displaced` overrides 2017 and 2018 for the displacement-triggered channel.
    - The b-jet triggers were active for only part of 2017 and 2018.

## Relevant Commands

- Use `norm` to register entries into `generatorSums.json`. 

See `python/kamui/README.md` for the flags and worked examples.

## Caveats

- Cross sections are stored unfiltered and `filterEfficiencies` are applied separately.
- The luminosity value moves with the golden JSON and normtag, which is why each Run 3 `source` records the exact brilcalc command. Re-run it against whatever golden JSON the data was filtered with.

Physics caveats per model are kept here so the configs stay readable.

**Exotic Higgs (exoticHiggs.json)**
- Higgs production at MH = 125 GeV, assuming BR(H -> LLP) = 1.
- Each run's numbers sit under their own key, so a Run 2 cross section can never normalize a Run 3 sample. The `run2` block is at 13 TeV, and Run 3 still needs its own `run3` block at 13.6 TeV.
- The Run 2 VH samples are generated with leptonic decays only, so their cross sections are just summed over the three lepton flavors.
  - `WplusH`: three times the inclusive W+H cross section times BR(W -> lv) for one lepton flavor.
  - `WminusH`: three times the inclusive W-H cross section times BR(W -> lv) for one lepton flavor.
- `ZH` is the qq-initiated piece, with the gg component split off into `ggZH`.
  - `ZH`: three times the ZH -> llH cross section for one lepton flavor, minus its gg-initiated part.
  - `ggZH`: three times the inclusive ggZH cross section times BR(Z -> ll) for one lepton flavor.
- Even though the `filterEfficiencies` are keyed by scalar mass, the filter itself is on gen-HT.
