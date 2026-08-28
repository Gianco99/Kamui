# config/crossSections

`README.md` covers the three files and the formula they feed. This is what to be careful about.

## The Denominator Is The Full Dataset, And The Code Enforces It

`normalization.denominator(sampleName)` has two failure modes and neither of them guesses.

- No entry, or an entry with no `sumGenWeight`, returns `None`. The sample has never been measured. A caller that treats `None` as 1.0 has silently normalized to nothing.
- `complete == False` raises `ValueError` naming both counts. That flag is set in `record()` whenever `nEvents` and `dasEvents` are both known and disagree, which is exactly the skimmed-or-capped case: the measured weight sum is smaller than the true one, so every yield built from it would come out too large. Re-measure over a complete production, do not divide by what is stored.

`complete` is only written when both counts exist. A fresh entry holding `dasEvents` alone has no `complete` key, and `denominator` returns `None` for it, which is the correct answer.

## The Genweight Producer Lives Outside The Skim

`kamuiNtuple_cfg.py` splits the table producers, pulling anything whose module name contains `genweight` out of the `kamuiTables` Task so the HLT skim cannot gate it. This looks like an inconsistency in the job configuration and is load-bearing: the `Runs` tree counters must accumulate over every generated event, and a skimmed ntuple whose `Runs` sums covered only surviving events would produce a wrong denominator that still looks like a valid measurement.

## measure() Is Quiet About Files With No Runs Tree

It skips them and keeps going, so a set of inputs that carries no `Runs` tree at all returns zeros. Those zeros are still written by `record()`, and the `complete` check is what catches them afterwards. Only point `--inputTask` at a production of the sample itself.

## record() Merges

It reads the existing entry and updates it, so a later `norm` run adding a weight sum keeps the `dasEvents` recorded earlier, and a DAS-only run does not erase a measurement. The write goes to a `.tmp` file and is moved into place with `os.replace`, so an interrupted run cannot leave a half-written JSON.

## This Config File Is Written By Code

`generatorSums.json` is the one config file the framework edits. `./kamui norm` rewrites it, which means the change shows up as a working-tree diff and has to be committed like any other config edit. Cross section files and `lumi.json` are only ever edited by hand.

## normalization.py Opens A Config File Directly

`./kamui check` forbids anything outside `configReaders/` from touching a config path, but it only scans for `CONFIG_DIR`, `SAMPLES_DIR`, `CONTENT_DIR`, `TRIGGERS_DIR` and `SITES_FILE`. `XSEC_DIR` and `LUMI_FILE` are outside that list, which is why `select/normalization.py` reads and writes `generatorSums.json` itself without tripping the check.

## Nothing Reads The Cross Sections Yet

`generatorSums.json` has a consumer in `normalization.py`. `exoticHiggs.json` and `lumi.json` have none: the weight formula lives in `exoticHiggs.json` as the `_weightFormula` string, and no code in the tree parses either file. Anything written to consume them is the first consumer, and gets to decide the reader's shape.

## filterEff Is Stored Separately

JMTucker multiplies cross section by filter efficiency at load time in `Samples.py:113`, so its stored signal cross sections are already the effective ones. The numbers here are unfiltered, and `filterEfficiencies` is a second factor the formula applies. Copying a JMTucker number into this file, or applying the efficiency again after using one of these, double-counts it.

## ZH And ggZH Are Two Entries

The `ZH` cross section here is the qq-initiated piece with the gg component subtracted out, and `ggZH` carries that component. Summing the two gives inclusive ZH. Both are per-flavour numbers already multiplied by three for the three lepton flavours. All the Higgs cross sections assume BR(H -> long-lived pair) = 1.

## Only One Cross Section File Exists

`exoticHiggs.json`. Stealth SUSY and RPV samples have `dasEvents` recorded in `generatorSums.json` and no cross sections anywhere in the tree, so they can be counted and not yet normalized.

## The One Measured Entry Is Deliberately Incomplete

`ZHToSSTo4d_mS55_ctau1mm_2018` is the only sample with a weight sum, measured over 2652 of its 49999 DAS events by the production task `normRun2Lep`, and carries `complete: false`. It is there as a worked example of the guard firing. Leave it; do not "fix" the flag.

## Run 3 Luminosity Keys Are Campaign Names

`Summer22` is 2022 pre-EE only and `Summer23` is 2023 pre-BPix only; the rest of each year is under `Summer22EE` and `Summer23BPix`. An era key that reads like a year is a sub-year value, and adding a sample under the wrong campaign name normalizes it to roughly a third or a half of the right luminosity. The sub-era values come from splitting the full-year golden JSON at runs 357900/359022 and 369802/369803, cuts that fall inside certified gaps, so the two halves reconstruct the full year lumi-section for lumi-section.

Each `source` names the golden JSON the value was integrated over, because the number moves with the golden and normtag vintage. Re-run `brilcalc` against whatever golden JSON the ntuples were actually filtered with before trusting a value to better than a percent. `channels.displaced` covers 2017 and 2018 alone, since `config/triggers/` has no Run 3 trigger list to define a Run 3 displaced channel.
