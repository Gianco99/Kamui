# Cross Sections and Generator Sums

The numbers that turn a count of selected events into an expected yield. Two files live here, and a third input, `config/lumi.json`, is documented below because it enters the same formula.

## The Formula

```
N_expected = lumi[pb^-1] * xsec[pb] * filterEff / sumGenWeight * sum(per-event weights of passing events)
```

`lumi` comes from `config/lumi.json`, `xsec` and `filterEff` from a cross section file here, and `sumGenWeight` from `generatorSums.json`. The string is recorded in `exoticHiggs.json` under `_weightFormula`.

## exoticHiggs.json

Higgs production cross sections at MH = 125 GeV, in picobarns, assuming BR(H -> long-lived pair) = 1. Multiply by whatever branching ratio you are assuming.

| process | xsec (pb) |
|---|---|
| ggH | 48.09 |
| VBFH | 3.813 |
| WplusH | 0.28623 |
| WminusH | 0.17943 |
| ZH | 0.07788 |
| ggZH | 0.011985 |
| ttH | 0.5306 |

The associated-production numbers are per-lepton-flavour values summed over three flavours, and `ZH` is the qq-initiated piece with the gg component split off into `ggZH`. Every entry carries a `source` string naming where in JMTucker the number came from.

`filterEfficiencies` holds the generator filter efficiency of the H -> SS -> 4d samples, keyed by scalar mass: 0.106 at 15 GeV, 0.085 at 40 GeV, 0.082 at 55 GeV. It depends only on the scalar mass.

Keys beginning with an underscore are commentary.

## generatorSums.json

One entry per sample name under `samples`, holding the denominator of the formula and the bookkeeping that proves it is trustworthy.

| field | meaning |
|---|---|
| `dasEvents` | Generated event count of the whole dataset, from DAS |
| `nEvents` | Sum of `genEventCount` over the files actually measured |
| `sumGenWeight` | Sum of `genEventSumw`, the normalization denominator |
| `sumGenWeight2` | Sum of `genEventSumw2`, for the statistical uncertainty |
| `source` | Which production task the measurement was made over, or `DAS` |
| `complete` | Whether `nEvents` equals `dasEvents` |

The sums are read from the run-level `Runs` tree written by the NanoAOD `genWeightsTable` producer, which sits outside the HLT skim in `kamuiNtuple_cfg.py` so that it sees every generated event.

These belong to the whole dataset as it exists on DAS. A skim, or a run with a capped file list, sees a subset of the generated events, and its weight sum is correspondingly smaller; used as a denominator it would inflate every yield by the inverse of the fraction processed, with nothing in the output to show it. `dasEvents` is what makes that detectable, and `complete` is the recorded verdict.

## Adding a Sample

1. Add the sample to its family file under `config/samples/`.
2. `./kamui norm --family <family>` asks DAS for the generated event count and records `dasEvents`. This works as soon as the sample exists, before any production.
3. Once a complete production of it exists, `./kamui norm --family <family> --inputTask <task>` opens those ntuples, sums the `Runs` counters, and fills in `nEvents`, `sumGenWeight` and `sumGenWeight2`.
4. A production mode with no cross section on file needs one adding to a cross section JSON here.

`norm` takes the same five sample selection flags as every other command: `--name`, `--family`, `--era`, `--tag`, `--match`. `--noDas` skips the DAS lookup, and `--inputBase` points at an EOS base other than the site stageout base.

`./kamui check` fails if any catalogued sample has no `dasEvents` recorded, and reports how many samples have a weight sum measured.

## config/lumi.json

Integrated luminosity per era, in inverse picobarns, under `eras`.

| era | lumi (pb^-1) |
|---|---|
| 2016APV | 19502 |
| 2016 | 16812 |
| 2017 | 42068 |
| 2018 | 59561 |
| Summer22 | 8086 |
| Summer22EE | 26675 |
| Summer23 | 18605 |
| Summer23BPix | 9677 |
| Summer24 | 109947 |

The Run 3 keys are CMS MC campaign names, so `Summer22` covers 2022 pre-EE alone, eras B/C/D, and the post-EE data lives under `Summer22EE`, eras E/F/G. The same split applies to `Summer23`, eras B/C, and `Summer23BPix`, era D. `Summer24` is the whole year, eras B through I. There is no 2025 entry.

Every value is certified-golden luminosity: `brilcalc totrecorded` with `-b 'STABLE BEAMS'` and `--normtag normtag_PHYSICS.json`, integrated over the official golden JSON for the era. The Run 3 entries were produced with brilws 3.9.4 on 2026-08-27 and each `source` names the golden JSON used, since the number moves with the golden and normtag vintage. The Run 2 entries carry the same basis, taken from JMTucker `AnalysisConstants.h`.

`channels` holds the smaller luminosity a channel integrates when its triggers were not live for a whole era. `channels.displaced` has 2017 at 37187 pb^-1 and 2018 at 54286 pb^-1, from the b-jet trigger constants. When normalizing that channel, use the channel value.
