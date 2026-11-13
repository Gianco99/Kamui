#!/bin/bash
## Runs the rewrite on every validated configuration into <outputs folder> (default outputs/final), two containers at a time and so at most two b-jet jobs at once: bash validation/runAll.sh [<outputs folder>]. Compare afterwards with validateAll.sh.
rewriteDir="$(dirname "$(dirname "$(realpath "$0")")")"
OUT="$(realpath -m "${1:-$rewriteDir/outputs/final}")"
EL7="/cvmfs/cms.cern.ch/common/cmssw-el7 -B /uscms_data --"
runOne() {
  echo "$(date +%T) start $1"
  timeout 7200 $EL7 bash "$rewriteDir/run.sh" "$OUT/$1" "${@:2}" > /dev/null 2>&1 < /dev/null
  echo "$(date +%T) done  $1: $(tail -1 "$OUT/$1/run.log" 2>/dev/null)"
}
laneA() {
  runOne productionDisplacement --channel displacement
  runOne sidebands/lepton_3x3 --channel lepton --ntracks 3x3 --btags all
  runOne sidebands/lepton_3x4 --channel lepton --ntracks 3x4 --btags all
  runOne sidebands/lepton_4x5 --channel lepton --ntracks 4x5 --btags all
  runOne extra/mcLepton20161Split --channel lepton --mc --year 20161 --btags 1 --bquarks 0 --minNpu 0 --maxNpu 27
  runOne extra/dataLepton2017p8 --channel lepton --year 2017p8 --btags all
}
laneB() {
  runOne productionLepton --channel lepton
  runOne sidebands/displacement2017_4x4 --channel displacement --year 2017 --ntracks 4x4 --btags all
  runOne sidebands/displacement2017_3x3 --channel displacement --year 2017 --ntracks 3x3 --btags all
  runOne sidebands/lepton_4x4 --channel lepton --ntracks 4x4 --btags all
  runOne sidebands/lepton_3x5 --channel lepton --ntracks 3x5 --btags all
  runOne mcLepton20161 --channel lepton --mc --year 20161 --btags all
  runOne extra/mcDisplacement20161Nobtags --channel displacement --mc --year 20161 --btags 0
}
laneA & laneB & wait
echo "$(date +%T) all done"
