"""
Makes the extra reference copies for the paths the first validation did not run: the original source (reference/2v_from_jets.cc) with only main() changed to run one configuration.

Usage: python3 makeExtraReferences.py

Writes rewrite/referenceExtra/<test>/ with the edited source, the reference Makefile, the weight helper and a job.sh that builds and runs it. Every replaced line is asserted to occur exactly once.
"""

# Import Block

## Standard Python imports
import os
import shutil

B = "/uscms/home/gdecastr/nobackup/work/BackgroundTemplateRebuild"
C = "/uscms_data/d3/gdecastr/work/BackgroundTemplateRebuild"
YEAR_LINE = '  for (const char* year : { "run2",}) { //{"20161", "20162", "2017", "2018", "2017p8", "run2"}) { //change depending on year run'
PARS_LINE = "      ConstructDvvcParameters pars2 = pars.year(year).ntracks(ntracks);"
DEFAULT_LINE = '      construct_dvvc(pars2,                                     TString::Format("2v_from_jets_%s_%dtrack_default_%s.root", year, ntracks, version));'
BTAGS_LINE = '      construct_dvvc(pars2.btags(1),     TString::Format("2v_from_jets_%s_%dtrack_btags_%s.root", year, ntracks, version));'
NOBTAGS_LINE = '      construct_dvvc(pars2.btags(0),     TString::Format("2v_from_jets_%s_%dtrack_nobtags_%s.root", year, ntracks, version));'
LEPTON_LINES = ('const std::string ulversion = "ULV30Lepm"; //Use for Lepton triggered samples\n//const std::string ulversion = "ULV30BvetoLHTm"; //Use for bjet triggered samples',
                '//const std::string ulversion = "ULV30Lepm"; //Use for Lepton triggered samples\nconst std::string ulversion = "ULV30BvetoLHTm"; //Use for bjet triggered samples')

# test name: (displacement channel, year, extra parameters, output file name the rewrite writes)
TESTS = {
    "mcLepton20161Split": (False, "20161", ".is_mc(true).btags(1).bquarks(0).min_npu(0).max_npu(27)", "2v_from_jets_20161_5track_btags_nobquarks_npu0to27_ULV30Lepm.root"),
    "mcDisplacement20161Nobtags": (True, "20161", ".is_mc(true).btags(0)", "2v_from_jets_20161_5track_nobtags_ULV30BvetoLHTm.root"),
    "dataLepton2017p8Npu": (False, "2017p8", ".min_npu(0).max_npu(27)", "2v_from_jets_2017p8_5track_npu0to27_ULV30Lepm.root"),
}


def replaceOnce(text, old, new):
    """Replaces old by new, asserting that old occurs exactly once."""
    assert text.count(old) == 1, f"expected exactly one occurrence of: {old[:80]}"
    return text.replace(old, new)


source = open(f"{B}/reference/2v_from_jets.cc").read()
for test, (displacement, year, extra, fileName) in TESTS.items():
    text = replaceOnce(source, YEAR_LINE, YEAR_LINE.replace('{ "run2",}', '{ "%s",}' % year, 1))
    text = replaceOnce(text, PARS_LINE, PARS_LINE.replace("ntracks(ntracks);", f"ntracks(ntracks){extra};"))
    text = replaceOnce(text, DEFAULT_LINE, f'      construct_dvvc(pars2, "{fileName}");')
    text = replaceOnce(text, BTAGS_LINE, "      if (false) " + BTAGS_LINE.lstrip())
    text = replaceOnce(text, NOBTAGS_LINE, "      if (false) " + NOBTAGS_LINE.lstrip())
    if displacement:
        text = replaceOnce(text, *LEPTON_LINES)
    d = f"{B}/rewrite/referenceExtra/{test}"
    os.makedirs(f"{d}/cb_vals", exist_ok=True)
    open(f"{d}/2v_from_jets.cc", "w").write(text)
    shutil.copy(f"{B}/reference/Makefile", d)
    shutil.copy(f"{B}/reference/2v_from_jets_new.py", d)
    open(f"{d}/job.sh", "w").write(f"""#!/bin/bash
## Builds and runs the original reference source with main() edited for {test}: {year}{extra}
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /uscms_data/d3/gdecastr/work/DVCode/mfv_10648/src && eval "$(scramv1 runtime -sh)"
cd {C}/rewrite/referenceExtra/{test} && make > build.log 2>&1 && /usr/bin/time -v timeout 5400 ./2v_from_jets.exe > run.log 2>&1; echo "exit $?" >> run.log
""")
    print(test, fileName)
