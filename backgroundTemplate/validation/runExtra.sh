#!/bin/bash
## Runs the extra validation: lane A builds and runs the three original copies in BackgroundTemplateRebuild/rewrite/referenceExtra (outside the repo), lane B runs the rewrite with the matching options into outputs/final/extra. At most two containers at a time.
C=/uscms_data/d3/gdecastr/work/BackgroundTemplateRebuild/rewrite
rewriteDir="$(dirname "$(dirname "$(realpath "$0")")")"
EL7="/cvmfs/cms.cern.ch/common/cmssw-el7 -B /uscms_data --"
laneA() {
  for t in mcLepton20161Split mcDisplacement20161Nobtags dataLepton2017p8Npu; do
    echo "$(date +%T) original $t start"; timeout 6000 $EL7 bash $C/referenceExtra/$t/job.sh > $C/referenceExtra/$t/container.log 2>&1; echo "$(date +%T) original $t done"
  done
}
laneB() {
  runOne() { echo "$(date +%T) rewrite $1 start"; timeout 5400 $EL7 bash "$rewriteDir/run.sh" "$rewriteDir/outputs/final/extra/$1" "${@:2}" > /dev/null 2>&1; echo "$(date +%T) rewrite $1 done"; }
  runOne mcLepton20161Split --mc --year 20161 --btags 1 --bquarks 0 --minNpu 0 --maxNpu 27
  runOne mcDisplacement20161Nobtags --channel displacement --mc --year 20161 --btags 0
  runOne dataLepton2017p8Npu --year 2017p8 --btags all --minNpu 0 --maxNpu 27
}
laneA & laneB & wait
echo "$(date +%T) all done"
