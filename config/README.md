# Config

This folder holds all the configuration files the framework reads. Each subdirectory has its own documentation.

| Path | What it holds |
|---|---|
| `samples/` | Which datasets to process. See `samples/README.md`. |
| `content/` | Collections describe sets of physics objects. Presets combine them into what we want to include in ntuples. See `content/README.md`. |
| `triggers/` | The HLT paths we impose. See `triggers/README.md`. |
| `selections/` | The ordered event-level cuts. See `selections/README.md`. |
| `normalizations/` | Cross sections, luminosities, and per-sample generator sums to normalize yields. See `normalizations/README.md`. |
| `sites.json` | Storage paths, redirectors, CRAB site, CMSSW release. |
## sites.json

Standalone file containing the configuration for CMSSW, EOS, Condor and CRAB

| Key | Meaning |
|---|---|
| `eosRedirector` | The xrootd door for our EOS area |
| `sourceRedirector` | The xrootd door for reading datasets off the grid |
| `stageoutBase` | Where Condor outputs are written |
| `crabStageoutBase` | Where CRAB outputs are written |
| `miniaodDir` | The subdirectory under `stageoutBase` holding raw MiniAOD copies |
| `crabStorageSite` | The site CRAB is told to deliver to |
| `cmssw.version` | The CMSSW release jobs run in |
| `cmssw.scramArch` | The architecture that release was built for |

Paths use `$USER`, filled in when the file is read.
