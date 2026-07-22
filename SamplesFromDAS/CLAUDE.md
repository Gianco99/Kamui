# SamplesFromDAS

## samples.json key reference

| Key | Meaning |
|---|---|
| `outputEosDir` | EOS path (no redirector prefix) |
| `eosRedirector` | xrootd redirector for EOS destination |
| `sourceRedirector` | xrootd redirector for reading from the grid |
| `dasName` | Full CMS DAS dataset path |
| `dasInstance` | `prod/global` for official MC; `prod/phys03` for USER datasets |
| `nFilesFor10k` | Files needed for ~10k events — caps copies for preliminary studies |

## nFilesFor10k values

| Sample | Events/file | nFilesFor10k |
|---|---|---|
| ggH-2S-4D_mS55_ctau10mm_2024 | ~28,000 | 1 |
| StopStopbar-2Dbar2D_M400_ctau10mm_2024 | ~10,000 | 1 |
| StealthSHH_mStop325_mSo100_ctau10mm_2024 | ~130 | 100 |
| ZH-2S-4D_mS55_ctau1mm_2024 | 20–5,860 (very uneven) | 21 (=12,220 evts) |

## ZH-2S-4D_mS55_ctau1mm_2024 caveat
Z decay is **inclusive** (gen-checked 2026-07-21: 68% qq, 22% νν, 10% ℓℓ), unlike the
Run 2 `ZH_HToSSTodddd_ZToLL` samples. Only ~10% of events (~1.2k of the staged 12.2k)
are in the Run 2 leptonic phase space. For a like-for-like leptonic comparison, stage the
full dataset (84 files, 13.4 GB, 130k evts → ~13k Z→ℓℓ) or filter on gen leptons.

## Notes
- `fetchSamples.py` requires `voms-proxy-init --voms cms`; `dumpBranches.py` does not.
- EOS destination: `root://cmseos.fnal.gov//store/user/lpcdisplacedvertices/gdecastr/Run3Samples/<sampleName>/`
