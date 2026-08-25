Kamui - Run 3 Displaced Vertex Analysis Framework
=================================================

A spiritual successor to JMTucker.

The philosophy behind this repo is to utilize easy to edit, human-readable configuration files that compartmentalize the physics we want to study. It contains a CLI called Kamui which allows users to perform any task. It also utilizes CLAUDE.md and README.txt files in each subdirectory to track important design choices so that both the user or an AI helper are able to easily understand the code.

Important Note: Even though AI is used in the development is this framework, every single commit and piece of written code MUST BE HUMAN-REVIEWED before it is merged!


Layout
------
The root directory holds this README.txt, a CLAUDE.md documenting general design choices, the kamui CLI entry-point and all the subdirectories.

  kamui             The CLI entry point
  python/kamui/     The framework itself
  SamplesFromDAS/   DAS catalog, content configs, trigger configs, job submission, cmsRun config
  docs/             Transient planning and reference documents
  CLAUDE.md         Conventions for the AI

Each subdirectory carries its own CLAUDE.md holding the agent-facing context for it.


Quick Start - CMSSW
-------------------
First time only! Create a CMSSW_16_1_2 release area wherever you keep them:

  source /cvmfs/cms.cern.ch/cmsset_default.sh
  export SCRAM_ARCH=el9_amd64_gcc13
  cmsrel CMSSW_16_1_2

Then per session, from that release's src/:

  source /cvmfs/cms.cern.ch/cmsset_default.sh
  export SCRAM_ARCH=el9_amd64_gcc13
  cmsenv
  voms-proxy-init --rfc --voms cms -valid 192:00


Quick Start - Kamui
-------------------
Everything runs through one command, ./kamui, from the repo root.

  ./kamui --help                       List every command

The full command reference are documented in detail in python/kamui/README.txt.
