#!/usr/bin/env python

from JMTucker.Tools.ROOTTools import *
import JMTucker.Tools.Samples as Samples
import JMTucker.MFVNeutralino.AnalysisConstants as ac
import ROOT
import sys

def return_partial_weight():
    s = getattr(Samples, sys.argv[1])

    #Scale factors below taken from MFVNeutralino/interface/AnalysisConstants.h, and thus should match before running
    
    #Use this weight when running lepton triggered samples
    if "20161" in s.name:
        if "ULV30Lepm" in sys.argv[2]:
            #weight = 19502*s.partial_weight('root://cmsxrootd.fnal.gov//store/group/lpclonglived/alecduqu/MiniTree_LepIPCut_Lepton_SF_20161correctionsLepm_noef/%s.root' % s.name)
            weight = 19502*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag001Lepm/%s.root' % s.name)
        else:
            #weight = 19502*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree__tagTestFixTrigThresholdsBvetoLHTm/%s.root' % s.name)
            weight = 19502*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag004BvetoLHTm/%s.root' % s.name)
    elif "20162" in s.name:
        if "ULV30Lepm" in sys.argv[2]:
            #weight = 16812*s.partial_weight('root://cmsxrootd.fnal.gov//store/group/lpclonglived/alecduqu/MiniTree_LepIPCut_Lepton_SF_20162correctionsLepm_noef/%s.root' % s.name)
            weight = 16812*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag001Lepm/%s.root' % s.name)
        else:
            #weight = 16812*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree__tagTestFixTrigThresholdsBvetoLHTm/%s.root' % s.name)
            weight = 16812*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag004BvetoLHTm/%s.root' % s.name)
    elif "2018" in s.name:
        if "ULV30Lepm" in sys.argv[2]:
            #weight = 59561*s.partial_weight('/uscms/home/alecduqu/crab_dirs/MiniTree_LepIPCut_eventweights_Lepton_SF_2018correctionsLepm_noef/%s.root' % s.name)
            weight = 59561*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag001Lepm/%s.root' % s.name)
        else:
            #weight = 59561*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree__tagTestFixTrigThresholdsBvetoLHTm/%s.root' % s.name)
            weight = 59561*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag004BvetoLHTm/%s.root' % s.name)
    elif "2017" in s.name: #so 2017
        if "ULV30Lepm" in sys.argv[2]:
            #weight = 42068*s.partial_weight('root://cmsxrootd.fnal.gov//store/group/lpclonglived/alecduqu/MiniTree_LepIPCut_Lepton_SF_correctionsLepm_noef/%s.root' % s.name)
            weight = 42068*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag001Lepm/%s.root' % s.name)
        else:
            #weight = 42068*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree__tagTestFixTrigThresholdsBvetoLHTm/%s.root' % s.name)
            weight = 42068*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag004BvetoLHTm/%s.root' % s.name)
    elif "run2" in s.name:
        if "ULV30Lepm" in sys.argv[2]:
            weight = 137943*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag001Lepm/%s.root' % s.name)
        else:
            weight = 137943*s.partial_weight('/uscms_data/d3/joeyr/crabdirs/MiniTree_tag004BvetoLHTm/%s.root' % s.name)
    

    return weight

print(return_partial_weight())


