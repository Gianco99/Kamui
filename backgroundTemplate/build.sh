#!/bin/bash
## Builds 2v_from_jets.exe inside cmssw-el7: /cvmfs/cms.cern.ch/common/cmssw-el7 -B /uscms_data -- bash build.sh. The full compiler output goes to build.log. Set CMSSW_SRC to use another CMSSW_10_6 area.
CMSSW_SRC=${CMSSW_SRC:-/uscms_data/d3/gdecastr/work/DVCode/mfv_10648/src}
rewriteDir="$(dirname "$(realpath "$0")")"
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$CMSSW_SRC" && eval "$(scramv1 runtime -sh)"
cd "${rewriteDir:?}" || exit 1
if make > build.log 2>&1; then
  echo "Built $rewriteDir/2v_from_jets.exe"
else
  grep -E "error|Error" build.log | head -30
  echo "Build failed, see $rewriteDir/build.log"
  exit 1
fi
