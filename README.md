# Kamui: Run 3 Analysis Framework
The philosophy behind this repo is to utilize easy to edit, human-readable configuration files that compartmentalize the physics we want to study. It contains a CLI called Kamui which allows users to perform common tasks. It also utilizes CLAUDE.md and README.md files in relevant subdirectories to track important design choices so that both the user or an AI helper are able to easily understand the code.

**Important Note:** Even though AI is used in the development of this framework, every single commit and piece of written code MUST BE HUMAN-REVIEWED before it is merged!

## Layout

| Path | What it holds |
|---|---|
| `kamui` | The CLI entry point |
| `python/kamui/` | The CLI software and documentation |
| `config/` | All of the physics packaged into configuration files |
| `ntupleProduction/` | Step 1: DAS datasets to ntuples |
| `ntupleSelection/` | Step 2: Selections applied to ntuples |
| `tools/` | Standalone scripts that read what the framework produced, or what it is about to consume |
| `CLAUDE.md` | Conventions for the AI |
## The Framework

A dataset is processed in two stages, each driven by their own configuration files:

1. **`ntupleProduction`** reads a DAS dataset named in `config/samples/` and writes ntuples. The presets from `config/content/` define the collections (with any predefined skim) we save. Jobs run on LPC condor or on CRAB.

2. **`ntupleSelection`** applies an event selection from `config/selections/` to those ntuples. Because the output has the same structure as the input, the stage is repeatable with multiple selections.

An **ntuple** here is a ROOT file holding an `Events` tree with one entry per event, carrying the collections and variables a content preset names.

Cross sections, filter efficiencies, generator weight sums and luminosities live in `config/normalizations/`. These are only applied in post-processing when reporting or analyzing yields, not directly to the ntuples.

We have performed a validation against [JMTucker](https://github.com/DisplacedVertices/cmssw-usercode/tree/UL_Lepton) using the Low-HT analysis' Run 2 selections reproduced in `config/selections/`. Ten cases reproduce event-by-event, covering both the lepton- and displacement-triggered channels across all four Run 2 eras. The denominators are the trigger-skimmed ntuples rather than the full datasets, so they differ from JMTucker's unfiltered totals.
## Quick start - CMSSW

First-time setup only! Create a CMSSW_16_1_2 release area in a convenient location:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el9_amd64_gcc13
cmsrel CMSSW_16_1_2
```

Then per session, from that release's `src/`:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el9_amd64_gcc13
cmsenv
voms-proxy-init --rfc --voms cms -valid 192:00
```

## Quick start - Kamui

Everything runs through one command, `./kamui`, from the repo root.

```bash
./kamui --help          # Lists every command
```

The full reference, with every flag, is in [python/kamui/README.md](python/kamui/README.md).
