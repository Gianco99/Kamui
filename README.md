# Kamui: Run 3 Displaced Vertex Analysis Framework

A spiritual successor to JMTucker.

The philosophy behind this repo is to utilize easy to edit, human-readable configuration files that compartmentalize the physics we want to study. It contains a CLI called Kamui which allows users to perform any task. It also utilizes CLAUDE.md and README.md files in each subdirectory to track important design choices so that both the user or an AI helper are able to easily understand the code.

**Important Note:** Even though AI is used in the development of this framework, every single commit and piece of written code MUST BE HUMAN-REVIEWED before it is merged!

## Layout

| Path | What it holds |
|---|---|
| `kamui` | The CLI entry point |
| `python/kamui/` | The framework itself, shared by every stage |
| `config/` | All of the physics packaged into configuration files |
| `ntupleProduction/` | Step 1: DAS datasets to  ntuples|
| `ntupleSelection/` | Step 2: Selections applied to ntuples  |
| `tools/` | Standalone scripts for validating results |
| `docs/` | Reference documents for past and future studies |
| `CLAUDE.md` | Conventions for the AI |

Subdirectories carry their own `README.md` for humans and `CLAUDE.md` for agents.

## The Framework

A dataset is processed in two stages, each driven by their own configuration files:

1. **`ntupleProduction`** reads a DAS dataset named in `config/samples/` and writes ntuples. The presets from `config/content/` define the content we save; they name the collections and the per-object variables to store, in addition to any skims. Jobs run on LPC condor or on CRAB.

2. **`ntupleSelection`** applies an event selection from `config/selections/` to those ntuples. Because the output has the same structure as the input, the stage is repeatable with multiple selections.

An **ntuple** here is a ROOT file holding an `Events` tree with one entry per event, carrying the collections and variables a content preset names.

Cross sections, filter efficiencies, generator weight sums and luminosities live in `config/normalizations/` and `config/normalizations/lumi.json`. These are only applied in post-processing when reporting or analyzing yields, not directly to the ntuples.

We have performed a validation against [JMTucker](https://github.com/DisplacedVertices/cmssw-usercode/tree/UL_Lepton) using the Low-HT analysis' Run 2 selections reproduced in `config/selections/`. We are able to reproduce results event-by-event, after **only applying the trigger selection**, in both the lepton- and displacement-triggered channels for representative signal points. 

TODO: Link the docs file with this study. 

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
./kamui check           # Validate every configuration file
```

The full reference, with every flag, is in [python/kamui/README.md](python/kamui/README.md). Below are the commands we currently support:

| Command | What it does |
|---|---|
| `list` | Show all available samples |
| `content` | Show presets declaring what we save in ntuples |
| `query` | Query DAS for how many files, events and GB each selected sample holds |
| `find` | Unrestricted DAS dataset search |
| `stage` | Copy raw MiniAOD to EOS |
| `submit` | Produce ntuples by submitting to condor or CRAB |
| `resubmit` | Rerun failed jobs |
| `status` | Status of a submitted task |
| `select` | Apply an event selection to ntuples |
| `cutflow` | Print the cutflow for a given task |
| `norm` | Measure and store weights for normalization |
| `check` | Validate configuration files |
| `cache` | Inspect or clear the DAS cache |


