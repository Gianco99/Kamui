## Builds 2v_from_jets.exe against the MiniNtuple/VertexAux copies in include/ (unchanged from Alec's checkout), ahead of CMSSW_BASE/src (CMSSW_10_6_48)
COPIES = include
## Linked in as in Alec's Makefile: the MFVNeutralinoFormats TriggerEnum files, TBB, CLHEP, two CMSSW release libraries and every library of CMSSW_BASE
SHADOWDEPS = $(wildcard $(CMSSW_BASE)/src/JMTucker/MFVNeutralinoFormats/*/TriggerEnum*) /cvmfs/cms.cern.ch/$(SCRAM_ARCH)/external/tbb/2019_U3-pafccj/lib/libtbb.so.2 /cvmfs/cms.cern.ch/$(SCRAM_ARCH)/external/clhep/2.4.0.0-pafccj2/lib/libCLHEP.so $(CMSSW_RELEASE_BASE)/lib/$(SCRAM_ARCH)/libDataFormatsCommon.so $(CMSSW_RELEASE_BASE)/lib/$(SCRAM_ARCH)/libDataFormatsCandidate.so $(CMSSW_BASE)/lib/$(SCRAM_ARCH)/*.so
ROOTFLAGS = $(shell root-config --cflags --libs)
INC = -I$(COPIES) -I${CMSSW_BASE}/src -I/cvmfs/cms.cern.ch/${SCRAM_ARCH}/external/boost/1.67.0-pafccj/include -I${CLHEP_PARAM_PATH}/include -I/cvmfs/cms.cern.ch/${SCRAM_ARCH}/external/tbb/2019_U3-pafccj/include -I${CMSSW_RELEASE_BASE}/src
all: 2v_from_jets.exe
MiniNtuple.o: $(COPIES)/JMTucker/MFVNeutralino/src/MiniNtuple.cc $(COPIES)/JMTucker/MFVNeutralino/interface/MiniNtuple.h
	g++ $(INC) -std=c++17 $(ROOTFLAGS) -c $< -o $@
2v_from_jets.exe: 2v_from_jets.cc MiniNtuple.o $(SHADOWDEPS)
	g++ -g -Wall $(INC) -std=c++17 $^ -o $@ $(ROOTFLAGS) -L/cvmfs/cms.cern.ch/slc7_amd64_gcc700/cms/cmssw/CMSSW_10_6_48/external/slc7_amd64_gcc700/lib/ -lboost_system -L/cvmfs/cms.cern.ch/slc7_amd64_gcc700/cms/cmssw/CMSSW_10_6_48/lib/slc7_amd64_gcc700/ -lDataFormatsTrackReco -lTrackingToolsTransientTrack -lMagneticFieldEngine -lDataFormatsProvenance -lFWCoreUtilities -lDataFormatsCommon -lDataFormatsVertexReco -lDataFormatsCandidate -lDataFormatsHepMCCandidate -lTrackingToolsIPTools -lRecoVertexVertexPrimitives -lRecoVertexAdaptiveVertexFinder -lRecoBTagBTagTools -lRecoVertexVertexTools -lFWCoreParameterSet -lRecoVertexKalmanVertexFit -lGenVector
clean:
	rm -f 2v_from_jets.exe MiniNtuple.o
