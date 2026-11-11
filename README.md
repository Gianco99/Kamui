# Kamui: Run 3 Analysis Framework

Kamui is the framework for our Run 3 CMS DV analysis. A DV is a vertex fit from displaced tracks, the tracks that pass far from the beamspot. Kamui reads MiniAOD datasets, writes ntuples that keep only the objects and variables we choose, and applies event selections to those ntuples. An ntuple here is a ROOT file holding an `Events` tree with one entry per event.

The physics lives in easy-to-edit, human-readable configuration files under `config/`, one folder per topic, and the `./kamui` CLI runs each step. Each relevant subdirectory has a README.md that records its important design choices and ends with a Caveats section, so you and an AI helper can both follow the code.

**Important Note:** AI helps develop this framework, but every commit and piece of written code MUST BE HUMAN-REVIEWED before it is merged!

## The Framework

A dataset goes through two stages, each driven by its own configuration files:

1. `ntupleProduction` reads a DAS dataset named in `config/samples/` and writes ntuples. The sample's content preset, in `config/content/`, decides what they keep: a set of collections, such as jets, each listing the variables to save. A preset can also skim, keeping only the events that fire chosen triggers. Jobs run on LPC condor or on CRAB.
2. `ntupleSelection` applies an event selection from `config/selections/` to those ntuples. Its output has the same branches as its input. To apply several selections at once, list them with commas: `--selection lepton,dv3x4` applies `lepton` and then `dv3x4`.

On the command line the two stages look like this, with your own names in place of the placeholders:

```bash
./kamui submit --tag <tag> --task <ntupleTask>
./kamui select --tag <tag> --selection <selection> --task <selectionTask> --inputTask <ntupleTask>
```

Cross sections, filter efficiencies, generator weight sums and luminosities live in `config/normalizations/`. They are applied only in post-processing, when you report or analyze yields.

## Layout

| Path | What it holds |
|---|---|
| `kamui` | The CLI entry point |
| `python/kamui/` | The CLI software and documentation |
| `config/` | All of the physics packaged into configuration files |
| `ntupleProduction/` | Step 1: DAS datasets to ntuples |
| `ntupleSelection/` | Step 2: Selections applied to ntuples. `select` creates it when it runs, with `jobs/` for condor passes and `out/` for local passes, and `.gitignore` keeps both out of git |
| `vertexing/` | DV reconstruction |
| `tools/` | Standalone scripts that inspect the framework's inputs and outputs |
| `Bugs/` | Known bugs and open issues, one file each saying where the problem lives and how to fix it. `jmtucker/adapted/` holds bugs in JMTucker code that Kamui ports, some copied on purpose so the two match. `jmtucker/notPorted/` holds bugs in JMTucker code that Kamui has no counterpart to. `backgroundTemplate/` holds bugs in Alec's background-template code. Each file's Template code line cites his uncommitted version, snapshotted in `/uscms/home/gdecastr/nobackup/work/BackgroundTemplateRebuild/alecSnapshot_2026-11-05_1640`, and the standalone rewrite of that code is in `/uscms/home/gdecastr/nobackup/work/BackgroundTemplateRebuild/rewrite` until it moves into Kamui. `openIssues/` holds problems in Kamui itself |
| `slides/` | The v0.1 slides, as a PDF |
| `CLAUDE.md` | Conventions for the AI |

## Quick Start: CMSSW

Do this once: create a CMSSW_16_1_2 release area wherever is convenient.

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el9_amd64_gcc13
cmsrel CMSSW_16_1_2
```

Then build the DV plugins into it, replacing `/path/to/Kamui` with the path to your Kamui clone:

```bash
cd CMSSW_16_1_2/src
cmsenv
mkdir Kamui
ln -s /path/to/Kamui/vertexing Kamui/Vertexing
scram b -j8
```

After that, start every session by running this from that release's `src/`:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el9_amd64_gcc13
cmsenv
voms-proxy-init --rfc --voms cms -valid 192:00
```

## Quick Start: Kamui

Everything runs through one command, `./kamui`, from the repo root.

```bash
./kamui --help          # Lists every command
```

The full reference, with every flag, is in [python/kamui/README.md](python/kamui/README.md).
