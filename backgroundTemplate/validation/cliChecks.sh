#!/bin/bash
## Runs the command-line checks inside cmssw-el7 and prints each command's exit code and first message line: /cvmfs/cms.cern.ch/common/cmssw-el7 -B /uscms_data -- bash validation/cliChecks.sh
CMSSW_SRC=${CMSSW_SRC:-/uscms_data/d3/gdecastr/work/DVCode/mfv_10648/src}
rewriteDir="$(dirname "$(dirname "$(realpath "$0")")")"
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$CMSSW_SRC" && eval "$(scramv1 runtime -sh)"
cd "${rewriteDir:?}" || exit 1
scratch=$(mktemp -d)
try() {
  ./2v_from_jets.exe "$@" > "$scratch/out" 2>&1 < /dev/null
  rc=$?
  out=$(grep -v "^Warning\|TClassTable" "$scratch/out" | head -2 | tr '\n' ' ')
  echo "exit $rc  [$*]  ${out:0:160}"
}
try
try --help
try --outDir $scratch/a
try --channel lepton
try --channel muon --outDir $scratch/a
try --channel lepton --outDir $scratch/a --year 2016
try --channel lepton --outDir $scratch/a --ntracks 6x6
try --channel lepton --outDir $scratch/a --btags 1,1
try --channel lepton --outDir $scratch/a --btags 1,
try --channel lepton --outDir $scratch/a --btags 2
try --channel lepton --outDir $scratch/a --bquarks 1
try --channel lepton --outDir $scratch/a --minNpu 10
try --channel lepton --outDir $scratch/a --mc --minNpu 30 --maxNpu 10
try --channel lepton --outDir $scratch/a --mc --maxNpu 300
try --channel lepton --outDir $scratch/a --mc --only20pc
try --channel lepton --outDir $scratch/a --mc=1
try --channel lepton --outDir $scratch/a --year
try --channel lepton --outDir $scratch/a --frobnicate
try --channel=lepton --outDir=$scratch/b --year=2017 --ntracks=4x4 --btags=all --bogusAfter
try --channel lepton --outDir /proc/forbidden
rm -rf "$scratch"
