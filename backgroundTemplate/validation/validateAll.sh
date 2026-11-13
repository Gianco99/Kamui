#!/bin/bash
## Compares every rewrite output in <outputs folder> (default outputs/final) with its reference: histograms (compareOutputs.py), stored bytes (compareRaw.py) and cb_vals.csv. The references live outside the repo, under B. Needs python3 with uproot: bash validation/validateAll.sh [<outputs folder>]
B=/uscms/home/gdecastr/nobackup/work/BackgroundTemplateRebuild
here="$(dirname "$(realpath "$0")")"
F="$(realpath -m "${1:-$(dirname "$here")/outputs/final}")"
check() {
  echo "== $1 vs $2"
  python3 "$here/compareOutputs.py" $1 $2
  python3 "$here/compareRaw.py" $1 $2 $3
  diff -q $1/cb_vals/cb_vals.csv $2/cb_vals/cb_vals.csv > /dev/null && echo "OK       cb_vals.csv" || echo "DIFFERS  cb_vals.csv"
}
check $B/reference $F/productionLepton
check $B/referenceBveto $F/productionDisplacement
check $B/rewrite/referenceMC/Lepm_5_20161 $F/mcLepton20161 --mc
for pair in Lepm_3:lepton_3x3 Lepm_4:lepton_4x4 Lepm_7:lepton_3x4 Lepm_8:lepton_3x5 Lepm_9:lepton_4x5 Bveto_4:displacement2017_4x4 Bveto_3:displacement2017_3x3; do
  check $B/rewrite/referenceSidebands/${pair%%:*} $F/sidebands/${pair##*:}
done
check $B/rewrite/referenceExtra/mcLepton20161Split $F/extra/mcLepton20161Split --mc
check $B/rewrite/referenceExtra/mcDisplacement20161Nobtags $F/extra/mcDisplacement20161Nobtags --mc
## Data MiniTrees store npu as 0, so the original's 2017p8 run with npu 0 to 27 is the plain 2017p8 run under another file name
R=$F/extra/dataLepton2017p8Reference
E=$B/rewrite/referenceExtra/dataLepton2017p8Npu
mkdir -p $R && ln -sfn $E/cb_vals $R/cb_vals && ln -sf $E/2v_from_jets_2017p8_5track_npu0to27_ULV30Lepm.root $R/2v_from_jets_2017p8_5track_default_ULV30Lepm.root
check $R $F/extra/dataLepton2017p8
