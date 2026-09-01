# Cross Sections and Generator Sums

The numbers that turn a count of selected events into an expected yield.
## The Normalization Formula

```
N_expected = lumi[pb^-1] * xsec[pb] * filterEff * sum(per-event weights of passing events) / sumGenWeight
```
- `lumi` comes from `config/lumi.json`
- `xsec` and `filterEff` from a cross section file here
- `sumGenWeight` from `generatorSums.json`.
## exoticHiggs.json

Higgs production cross sections at MH = 125 GeV, in picobarns, assuming BR(H -> long-lived pair) = 1.


The associated-production numbers are per-lepton-flavor summed over the three flavors.

- `ZH` is the qq-initiated piece with the gg component split off into `ggZH`.

`filterEfficiencies` holds the generator filter efficiency. 

- Ex: the Run 2 ggH samples that have a gen-HT cut.
## generatorSums.json

One entry per sample name under `samples`, holding the denominator of the normalization formula.
| field | meaning |
|---|---|
| `genEvents` | Generated event count of the whole dataset |
| `sumGenWeight` | Sum of `genEventSumw`, the normalization denominator |
| `sumGenWeight2` | Sum of `genEventSumw2`, for the statistical uncertainty  |

All three are read from the run-level `Runs` tree written by the NanoAOD `genWeightsTable` producer. DAS supplies the file paths, and the files are read over xrootd.
## lumi.json
Integrated luminosity per era, in inverse picobarns, under `eras`.


Run 3 comes from the certified-golden luminosity:

-  `brilcalc totrecorded` with `-b 'STABLE BEAMS'` and `--normtag normtag_PHYSICS.json`, integrated over the official golden JSON for the era. 

Run 2 entries are taken from JMTucker `AnalysisConstants.h`.

`channels` holds the smaller luminosity a channel integrates when its triggers were not active for a whole era. 

-   Ex: `channels.displaced` has 2017 at 37187 pb^-1 and 2018 at 54286 pb^-1, from the b-jet trigger constants.


## Relevant Commands

Use `norm` to register entries into `generatorSums.json`. 

See Kamui/python/kamui/README.md for the flags and worked examples.
