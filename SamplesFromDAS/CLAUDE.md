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

## Notes
- `fetchSamples.py` requires `voms-proxy-init --voms cms`; `dumpBranches.py` does not.
- EOS destination: `root://cmseos.fnal.gov//store/user/lpcdisplacedvertices/gdecastr/Run3Samples/<sampleName>/`
