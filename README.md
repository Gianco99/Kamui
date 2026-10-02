# Kamui: Run 3 Analysis Framework
The philosophy behind this repo is to use easy-to-edit, human-readable configuration files that compartmentalize the physics we want to study. It contains a CLI called Kamui for common tasks. Each relevant subdirectory has a README.md that tracks its important design choices and closes with a Caveats section, so both the user and an AI helper can easily understand the code.

**Important Note:** Even though AI is used in the development of this framework, every single commit and piece of written code MUST BE HUMAN-REVIEWED before it is merged!

## Layout

| Path | What it holds |
|---|---|
| `kamui` | The CLI entry point |
| `python/kamui/` | The CLI software and documentation |
| `config/` | All of the physics packaged into configuration files |
| `ntupleProduction/` | Step 1: DAS datasets to ntuples |
| `ntupleSelection/` | Step 2: Selections applied to ntuples |
| `vertexing/` | DV reconstruction |
| `tools/` | Standalone scripts that inspect the framework's inputs and outputs |
| `CLAUDE.md` | Conventions for the AI |
## The Framework

A dataset is processed in two stages, each driven by its own configuration files:

1. **`ntupleProduction`** reads a DAS dataset named in `config/samples/` and writes ntuples. The presets from `config/content/` define the collections (with any predefined skim) we save. Jobs run on LPC condor or on CRAB.

2. **`ntupleSelection`** applies an event selection from `config/selections/` to those ntuples. Because the output has the same structure as the input, the stage is repeatable with multiple selections.

An **ntuple** here is a ROOT file holding an `Events` tree with one entry per event, carrying the collections and variables a content preset names.

Cross sections, filter efficiencies, generator weight sums and luminosities live in `config/normalizations/`. These are applied only in post-processing, when reporting or analyzing yields.
## Quick start: CMSSW

First-time setup only! Create a CMSSW_16_1_2 release area in a convenient location:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el9_amd64_gcc13
cmsrel CMSSW_16_1_2
```

Then build the DV plugins into it. Replace `/path/to/Kamui` with your Kamui clone:

```bash
cd CMSSW_16_1_2/src
cmsenv
mkdir Kamui
ln -s /path/to/Kamui/vertexing Kamui/Vertexing
scram b -j8
```

Then per session, from that release's `src/`:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el9_amd64_gcc13
cmsenv
voms-proxy-init --rfc --voms cms -valid 192:00
```

## Quick start: Kamui

Everything runs through one command, `./kamui`, from the repo root.

```bash
./kamui --help          # Lists every command
```

The full reference, with every flag, is in [python/kamui/README.md](python/kamui/README.md).
