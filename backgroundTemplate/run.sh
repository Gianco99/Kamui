#!/bin/bash
## Runs 2v_from_jets.exe inside cmssw-el7 with the given options and logs to <outDir>/run.log: /cvmfs/cms.cern.ch/common/cmssw-el7 -B /uscms_data -- bash run.sh <outDir> --channel lepton [options]. Set CMSSW_SRC to use another CMSSW_10_6 area.
CMSSW_SRC=${CMSSW_SRC:-/uscms_data/d3/gdecastr/work/DVCode/mfv_10648/src}
rewriteDir="$(dirname "$(realpath "$0")")"
outDir="$(realpath -m "$1")"; shift
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$CMSSW_SRC" && eval "$(scramv1 runtime -sh)"
mkdir -p "$outDir" && cd "${rewriteDir:?}" && ./2v_from_jets.exe --outDir "$outDir" "$@" > "$outDir/run.log" 2>&1; echo "exit $?" >> "$outDir/run.log"
