# The generated-event count `norm` reads from a sample's NanoAOD can disagree with the MiniAOD a job reads.

- **Where:** `python/kamui/cli.py:345-357` (`_cmdNorm`) and `python/kamui/select/normalization.py:32-58` (`measureFromNano`).
- **Problem:** In 126 of 2,456 Run 3 entries the NanoAOD genEventCount differs from the MiniAOD's DAS event count, because one of the two lost lumis or files. In 69 the NanoAOD is short, so yields come out high: the worst, `compressedStop_mStop700_mLsp675_ctau1p0mm_2022`, has 0.60 of the MiniAOD count, and the rest are within 8%. In 57 the MiniAOD is short, by up to 5%. Comparing each `genEvents` in `config/normalizations/generatorSums.json` with `dasgoclient -query="summary dataset=<MiniAOD>"` reproduces the list.
- **Fix:** In `norm`, measure what the jobs read, or stop when the two counts disagree.
