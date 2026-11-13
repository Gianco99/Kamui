# Normalizations

This folder holds the numbers that turn a count of selected events into an expected yield: the luminosity of each era, the cross section of each process, and the generator weight sum of each sample.

## The Normalization Formula

You apply these numbers yourself in post-processing, when you report or analyze yields, with this formula:

```
N_expected = lumi[pb^-1] * xsec[pb] * filterEff * sum(per-event weights of passing events) / sumGenWeight
```

- `lumi` comes from `lumi.json`.
- `xsec` and `filterEff` come from a cross section file, one per physics model.
- `sumGenWeight` comes from `generatorSums.json`.

## Cross Section Files

Each physics model has one file, holding the cross sections its samples are normalized by. Its top level holds one block per run, `run2` or `run3`. Normalize a sample with the block of its era's run, so a Run 2 cross section never normalizes a Run 3 sample.

A small example with one process:

```
{
  "run2": {
    "processes": {
      "ggH": {"xsec": <pb>, "source": "<where the number came from>"}
    }
  }
}
```

A run block, under `run2` or `run3`, holds:

| Field | Meaning |
|---|---|
| **`processes`** (required) | The cross section of each production mode, keyed by process name |
| `filterEfficiencies` (optional) | The generator filter efficiency, keyed by signal model |

Each process under `processes` holds:

| Field | Meaning |
|---|---|
| **`xsec`** (required) | The cross section in picobarns |
| **`source`** (required) | Where the number came from |

Each model under `filterEfficiencies` holds:

| Field | Meaning |
|---|---|
| **`byScalarMass`** (required) | The efficiency, keyed by the scalar mass |
| **`source`** (required) | Where the numbers came from |

## generatorSums.json

`./kamui norm --write` writes this file, with one entry per sample name under `samples`.

The top level holds:

| Field | Meaning |
|---|---|
| **`samples`** (required) | The entries, keyed by sample name |

Each sample under `samples` holds:

| Field | Meaning |
|---|---|
| `genEvents` (optional) | The generated event count of the whole dataset |
| `sumGenWeight` (optional) | The sum of `genEventSumw`, the normalization denominator |
| `sumGenWeight2` (optional) | The sum of `genEventSumw2`, for the statistical uncertainty |

`norm` reads these numbers from the `Runs` tree of the sample's central NanoAOD.

## lumi.json

This file holds the integrated luminosity, in inverse picobarns.

The top level holds:

| Field | Meaning |
|---|---|
| **`eras`** (required) | The luminosity of each era, keyed by era name |
| `channels` (optional) | Per-channel overrides, keyed by channel and then by an era that `eras` lists |

Each era, under `eras` or under a channel, holds:

| Field | Meaning |
|---|---|
| **`lumi`** (required) | The integrated luminosity in pb^-1 |
| **`source`** (required) | Where the number came from |

The Run 3 values are the certified golden luminosity: `totrecorded` from `brilcalc lumi` with `-b 'STABLE BEAMS'` and `--normtag normtag_PHYSICS.json`, integrated over the era's official golden JSON. The Run 2 values are taken from JMTucker's `AnalysisConstants.h`.

`channels` holds the smaller luminosity a channel integrates when its triggers were not active for a whole era. For example, `channels.displaced` overrides 2017 and 2018 for the displacement-triggered channel, since the b-jet triggers were active for only part of those years.

## Relevant Commands

- `./kamui norm --write` registers entries in `generatorSums.json`.
- Run `./kamui check` after editing anything here. It fails on any JSON file here that is not well formatted.

The flags and worked examples are in `python/kamui/README.md`.

## Caveats

- Cross sections are stored before the generator filter, so apply the filter efficiency on top.
- The luminosity depends on the golden JSON and the normtag. Each Run 3 `source` records its exact brilcalc command, so rerun it against the golden JSON your data was filtered with.

### Exotic Higgs (`exoticHiggs.json`)

- The cross sections are for Higgs production at MH = 125 GeV, assuming BR(H->SS) = 1.
- The Run 2 VH samples decay the W or Z to leptons only, so the `WplusH`, `WminusH`, `ZH` and `ggZH` cross sections include that leptonic branching ratio, summed over the three lepton flavors.
- `ZH` is the qq-initiated part, and `ggZH` the gg-initiated part.
