// Builds the 2V background template from 1V events.
//
// Every 1V event whose DV passes the track sum pT and mass cuts goes into a pool, split into 8 categories by b tagging and number of reconstructed PVs (category()). Each anchor DV is paired with a random partner DV from its own category. The partner's tracks are moved so that both DVs share the anchor's PV, the ported JMTucker vertexer runs on the union of the two track lists, and the pair fills the template when two DVs with the right track counts come back. The template is h_c1v_sumdbv_revertexed_w_errorbars, filled at the sum of the two input dBVs.
//
// In 5x5 only the DVs with >= 5 tracks are anchors, and each one is paired twice: with any DV of its category, then with a >= 5-track DV. Every other mode pairs every pooled DV once, with any DV of its category.
//
// The outputs reproduce Alec's 2v_from_jets.cc bit for bit, known bugs included. Each kept bug is marked "Kept for the bit-identical check", with its file in Kamui's Bugs/ folder when it has one. Run with --help for the options.

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <vector>
// addOneVertexEvent, fillOneVertexHistograms and fillTwoVertexEvent take sqrt and atan2 of MiniNtuple floats through the float overloads of math.h, as the original does. std::hypot or a cast to double there changes the output.
#include <math.h>

#include "TCanvas.h"
#include "TChain.h"
#include "TF1.h"
#include "TFile.h"
#include "TH1.h"
#include "TH2.h"
#include "TLegend.h"
#include "TROOT.h"
#include "TStyle.h"
#include "TSystem.h"
#include "TVector2.h"

#include "DataFormats/Math/interface/deltaPhi.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"
#include "JMTucker/MFVNeutralino/interface/MiniNtuple.h"
#include "MagneticField/UniformEngine/interface/UniformMagneticField.h"
#include "RecoVertex/KalmanVertexFit/interface/KalmanVertexFitter.h"
#include "RecoVertex/VertexTools/interface/VertexDistance3D.h"
#include "RecoVertex/VertexTools/interface/VertexDistanceXY.h"
#include "TrackingTools/IPTools/interface/IPTools.h"
#include "TrackingTools/TransientTrack/interface/TransientTrack.h"

// ---------------------------------------------------------------- Constants

// 1V selection, on the tracks of the DV
constexpr double minTrackSumPt = 10;  // GeV
constexpr double minTrackMass = 5.5;  // GeV, every track taken as a pion
// Kept for the bit-identical check: Bugs/backgroundTemplate/templatePionMassDiffers.md (the 1V and 2V cuts use different pion masses)
constexpr double pionMass1v = 0.13957;
constexpr double pionMass2v = 0.1396;

// Pool categories: b-tagged events, then untagged ones, each split into the npv bins of category()
constexpr int nNpvBins = 4;
constexpr int nCategories = 2 * nNpvBins;

// Random-number seeds of the two pairing passes
constexpr unsigned anyPartnerSeed = 73;
constexpr unsigned fivePlusPartnerSeed = 86;

// 2V dVV histograms; larger values go into the last bin
constexpr int dvvNbins = 100;
constexpr double dvvBinWidth = 0.01;

// npu is stored in one byte, so this range keeps every event
constexpr int defaultMinNpu = 0;
constexpr int defaultMaxNpu = 255;

// Vertexer settings, named as in Kamui's DVProducer
constexpr double maxChi2PerDof = 5;                // Seeds and every refit
constexpr double sharedTracksMergeBelowSigma = 4;  // Two DVs sharing a track merge when their 3D distance is less significant than this
constexpr double sharedTracksKeepBelowSigma = 5;   // A shared track leaves any DV it is this many sigma or more from (3D impact parameter)
constexpr double sharedTracksTieBelowSigma = 1.5;  // Within this many sigma of both DVs, the shared track stays in the DV with more tracks
// mergeNearby: two DVs at about the same azimuth, close in xy and away from the beamspot
constexpr double mergeNearbyDeltaPhiBelow = 0.5;
constexpr double mergeNearbyDistance2dBelow = 0.0300;  // cm
constexpr double mergeNearbyDbvAbove = 0.0100;         // cm
const GlobalVector magneticField(0.0, 0.0, 3.8);       // Tesla, uniform

const std::string minitreeBase = "/uscms_data/d3/joeyr/crabdirs/";
// cb_vals.csv for bquark_fraction.py goes in this folder inside --outDir
const std::string cbValuesDir = "cb_vals";

// ---------------------------------------------------------------- Tables

// A trigger channel: its label in file names and the MiniTree folders it reads
struct Channel {
  std::string name, label, dataDir, data20pcDir, data20pcSuffix, mcDir;
};
// Kept for the bit-identical check (the weight helper normalizes lepton MC with MiniTree_tag001Lepm, while the events come from MiniTree_tag004Lepm). The displacement channel has no 20% MiniTrees, so, as in the original, --only20pc reads the per-era data files of its MC folder.
const Channel channels[] = {
    {"lepton", "ULV30Lepm", "MiniTree_tag004Lepm4_unblind_5trk_1vtx", "MiniTree_tag001Lepm", "_20pc", "MiniTree_tag004Lepm"},
    {"displacement", "ULV30BvetoLHTm", "MiniTree_tag004BvetoLHTm4_unblind_5trk_1vtx", "MiniTree_tag004BvetoLHTm", "", "MiniTree_tag004BvetoLHTm"},
};

// A template mode: the track counts of the two DVs of the 2V region it stands for, ntk0 being the larger, and for 3x4, 3x5 and 4x5 the tree of their exact-count 2V events. The code is the original's number for the mode, used in file names.
struct NtracksMode {
  int code;
  std::string name;
  int ntk0, ntk1;
  std::string extraTree;
};
const NtracksMode ntracksModes[] = {
    {3, "3x3", 3, 3, ""}, {4, "4x4", 4, 4, ""}, {5, "5x5", 5, 5, ""},
    {7, "3x4", 4, 3, "mfvMiniTreeNtk3or4exact/t"}, {8, "3x5", 5, 3, "mfvMiniTreeNtk3or5exact/t"}, {9, "4x5", 5, 4, "mfvMiniTreeNtk4or5exact/t"},
};

// Which single years a --year value reads, in reading order. 20161 and 20162 are 2016 preVFP and postVFP.
const std::map<std::string, std::vector<std::string>> yearParts = {
    {"20161", {"20161"}}, {"20162", {"20162"}}, {"2017", {"2017"}}, {"2018", {"2018"}}, {"2017p8", {"2017", "2018"}}, {"run2", {"20161", "20162", "2017", "2018"}},
};

// Tight DeepJet working point per year, from BTagging.cc. The original finds the year in the sample name, which gives the same value for every sample listed here.
float bdiscCut(const std::string& year) { return year == "20161" ? 0.6502 : year == "20162" ? 0.6377 : year == "2017" ? 0.7476 : 0.7100; }

// Sample names, in reading order; the order fixes the pool indices and so the pairing. A {a,b} group expands to one name per entry, and MC names get "_<year>" appended.
struct SampleSet {
  std::string channel;
  bool mc;
  std::vector<std::string> years;
  std::string names;
};
const SampleSet sampleSets[] = {
    {"lepton", false, {"20161"}, "SingleMuon20161{B,C,D,E,F} SingleElectron20161{B,C,D,E,F}"},
    {"lepton", false, {"20162"}, "SingleMuon20162{F,G,H} SingleElectron20162{F,G,H}"},
    // Kept for the bit-identical check: Bugs/backgroundTemplate/templateSingleMuon2017BMissing.md
    {"lepton", false, {"2017"}, "SingleElectron2017{B,D,F} SingleMuon2017{D,F} SingleElectron2017{C,E} SingleMuon2017{C,E}"},
    {"lepton", false, {"2018"}, "SingleMuon2018{A,B,C,D} EGamma2018{A,B,C,D}"},
    {"displacement", false, {"20161"}, "BTagCSV20161{B,C,D,E,F} DisplacedJet20161{B,C,D,E,F}"},
    {"displacement", false, {"20162"}, "BTagCSV20162{F,G,H} DisplacedJet20162{F,G,H}"},
    {"displacement", false, {"2017"}, "BTagCSV2017{B,C,D,E,F} DisplacedJet2017{C,D,E,F}"},
    {"displacement", false, {"2018"}, "DisplacedJet2018{A,B,C,D} JetHT2018{A,B,C,D}"},
    {"lepton", true, {"20161", "20162"}, "dyjetstollM{10,50} qcdbctoept{020,030,080,170,250} qcdempt{015,020,030,050,080,120,170,300} qcdmupt15 ttbar wjetstolnu_{0j,1j,2j} ww wz zz"},
    {"lepton", true, {"2017"}, "dyjetstollM{10,50} qcdbctoept{015,020,030,080,170,250} qcdempt{020,030,050,080,120,170,300} qcdpt{15,20,30,50,80,120,170,300,470,600,800,1000}mupt5 ttbar wjetstolnu_{0j,1j,2j} ww wz zz"},
    {"lepton", true, {"2018"}, "dyjetstollM{10,50} qcdbctoept{015,020,030,080,170,250} qcdempt{015,020,030,050,080,120,170,300} qcdmupt15 ttbar wjetstolnu_{0j,1j,2j} ww wz zz"},
    {"displacement", true, {"20161", "20162"}, "qcdht{0100,0200,0300,0500,0700,1000,1500,2000} ttbar"},
    {"displacement", true, {"2017", "2018"}, "ttbar qcdht{0200,0300,0500,0700,1000,1500,2000}"},
};

// Every histogram of the output file, in writing order
struct HistogramSpec {
  std::string type;  // TH1D, TH1F, TH2D or TH2F; "again" writes an earlier histogram a second time
  const char* name;
  const char* title;
  int nx;
  double xlo, xhi;
  int ny;
  double ylo, yhi;
};
const HistogramSpec histogramSpecs[] = {
    {"TH1D", "h_1v_dbv", "only-one-vertex events;d_{BV} (cm);events", 200, 0, 2.0},
    // Written empty, like h_1v_dbv_dz
    {"TH1D", "h_1v_dbv_npult20", "only-one-vertex events;d_{BV} (cm);events", 200, 0, 2.0},
    {"TH1D", "h_1v_dbv_npugt20lt30", "only-one-vertex events;d_{BV} (cm);events", 200, 0, 2.0},
    {"TH1D", "h_1v_dbv_npugt30lt40", "only-one-vertex events;d_{BV} (cm);events", 200, 0, 2.0},
    {"TH1D", "h_1v_dbv_npugt40", "only-one-vertex events;d_{BV} (cm);events", 200, 0, 2.0},
    {"TH1F", "h_1v_costh2_onlytks0", "only-one-vertex events;cos(angle2{flight,momentum}) (only tracks, no jets);events", 302, -1.001, 1.001},
    {"TH1F", "h_1v_costh20", "only-one-vertex events;cos(angle2{flight,momentum});events", 302, -1.001, 1.001},
    {"TH1D", "h_1v_bs2derr", "#sigma(dist2d(SV, beamspot)) (cm)", 100, 0, 0.005},
    {"TH1D", "h_1v_rescale_bs2derr", "rescaled #sigma(dist2d(SV, beamspot)) (cm)", 100, 0, 0.005},
    {"TH1D", "h_1v__w", ";event weight;events", 100, 0, 10},
    {"TH1D", "h_1v_z", ";z (cm);events", 250, -1, 1},
    {"TH1D", "h_1v_dz", "only-one-vertex events;z distance from pv to sv (cm);events", 1000, -10, 10},
    {"TH1F", "h_1v_dpvsv", "only-one-vertex events;3D distance from pv to sv (cm);events", 500, 0, 10},
    {"TH2D", "h_1v_xy", "only-one-vertex events;x0 (cm);y0 (cm)", 250, -1.0, 1.0, 250, -1.0, 1.0},
    // Kept for the bit-identical check (titled dBV, filled with the distance to the PV)
    {"TH1D", "h_1v_dbv0", "only-one-vertex events;d_{BV}^{0} (cm);events", 1000, 0, 2.0},
    {"TH1D", "h_1v_dbv1", "only-one-vertex events;d_{BV}^{1} (cm);events", 1000, 0, 2.0},
    {"TH2D", "h_1v_dbv_dz", "only-one-vertex events;d_{BV} (cm); d_{z} (cm)", 1000, 0, 2.0, 1000, 0, 2.0},
    {"TH2D", "h_1v_dbv_bs2derr", "only-one-vertex events;d_{BV} (cm); #sigma(dist2d(SV, beamspot)) (cm)", 1000, 0, 2.0, 100, 0, 0.005},
    {"TH1F", "h_1v_phiv", "only-one-vertex events;vertex #phi;events", 50, -3.15, 3.15},
    {"TH1D", "h_1v_npu", "only-one-vertex events;# PU interactions;events", 100, 0, 100},
    {"TH1D", "h_1v_npv", "only-one-vertex events;# reconstructed pv;events", 100, 0, 100},
    {"TH1F", "h_1v_njets", "only-one-vertex events;number of jets;events", 20, 0, 20},
    {"TH1F", "h_1v_ht40", "only-one-vertex events;H_{T} of jets with p_{T} > 40 GeV;events", 200, 0, 5000},
    {"TH1F", "h_1v_phij", "only-one-vertex events;jets #phi;jets", 50, -3.15, 3.15},
    {"TH1F", "h_1v_dphijj", "only-one-vertex events;#Delta#phi_{JJ};jet pairs", 100, -3.1416, 3.1416},
    {"TH1F", "h_1v_dphijv", "only-one-vertex events;#Delta#phi_{JV};jet-vertex pairs", 100, -3.1416, 3.1416},
    {"TH1F", "h_1v_dphijvpt", "only-one-vertex events;p_{T}-weighted #Delta#phi_{JV};jet-vertex pairs", 100, -3.1416, 3.1416},
    {"TH1F", "h_1v_dphijvmin", "only-one-vertex events;#Delta#phi_{JV}^{min};events", 50, 0, 3.1416},
    {"TH1F", "h_2v_dbv", "two-vertex events;d_{BV} (cm);vertices", 1250, 0, 2.5},
    {"TH2F", "h_2v_dbv1_dbv0", "two-vertex events;d_{BV}^{0} (cm);d_{BV}^{1} (cm)", 1250, 0, 2.5, 1250, 0, 2.5},
    {"TH1F", "h_2v_dvv", "two-vertex events;d_{VV} (cm);events", dvvNbins, 0, dvvNbins * dvvBinWidth},
    {"TH1F", "h_2v_dvv3D", "two-vertex events;3D d_{VV} (cm);events", dvvNbins, 0, dvvNbins * dvvBinWidth},
    {"TH1F", "h_2v_sumdbv", "two-vertex events; #Sigma(d_{BV})  (cm);events", 200, 0., 4.0},
    {"TH1F", "h_2v_dphivv", "two-vertex events;#Delta#phi_{VV};events", 10, -3.15, 3.15},
    {"TH1F", "h_2v_absdphivv", "two-vertex events;|#Delta#phi_{VV}|;events", 5, 0, 3.15},
    {"TH1D", "h_2v_npu", "two-vertex events;# PU interactions;events", 100, 0, 100},
    {"TH1D", "h_2v_npv", "two-vertex events;# reconstructed pv;events", 100, 0, 100},
    {"TH1F", "h_c1v_dvv3D_w_errorbars", "constructed from only-one-vertex events;3D d_{VV} (cm);events", 800, 0, 4},
    {"TH1F", "h_c1v_dvv3D_revertexed_w_errorbars", "constructed from only-one-vertex events;3D d_{VV} (cm);events", 800, 0, 4},
    {"TH1F", "h_c1v_sumdbv_revertexed_w_errorbars", "constructed from only-one-vertex events;#Sigma(d_{BV}) (cm);events", 200, 0, 4.0},
    {"TH1F", "h_c1v_absdphivv_revertexed_w_errorbars", "constructed from only-one-vertex events;|#Delta#phi_{VV}|;events", 5, 0, 3.15},
    {"TH1F", "h_c1v_sumdbv_w_errorbars", "constructed from only-one-vertex events;#Sigma(d_{BV}) (cm);events", 200, 0, 4.0},
    // Kept for the bit-identical check: the original writes this histogram twice
    {"again", "h_c1v_absdphivv_revertexed_w_errorbars"},
    {"TH2F", "h_c1v_ntrk0_ntrk1", "constructed from only-one-vertex events;# vtx0 trks;# vtx1 trks", 11, 0, 11, 11, 0, 11},
};

// ---------------------------------------------------------------- Small helpers

// Stops on a mistake in the command line
[[noreturn]] void usageError(const std::string& message) {
  std::cerr << "Error: " << message << "\nRun with --help for the options." << std::endl;
  exit(1);
}

// Stops on a problem while running
[[noreturn]] void fail(const std::string& message) {
  std::cerr << "Error: " << message << std::endl;
  exit(1);
}

std::vector<std::string> split(const std::string& s, char separator) {
  std::vector<std::string> parts;
  std::istringstream in(s);
  for (std::string part; std::getline(in, part, separator);)
    parts.push_back(part);
  return parts;
}

// Expands "qcdht{0100,0200}" into qcdht0100 and qcdht0200; names are separated by spaces
std::vector<std::string> expandNames(const std::string& spec) {
  std::vector<std::string> names;
  for (const std::string& token : split(spec, ' ')) {
    const size_t open = token.find('{'), close = token.find('}');
    if (open == std::string::npos) {
      names.push_back(token);
      continue;
    }
    for (const std::string& entry : split(token.substr(open + 1, close - open - 1), ','))
      names.push_back(token.substr(0, open) + entry + token.substr(close + 1));
  }
  return names;
}

// The MC weight of a sample (cross section times luminosity over generated events) from 2v_from_jets_new.py. The helper imports JMTucker modules, so it runs with the python2 of the CMSSW_10_6 environment.
float mcWeight(const std::string& helper, const std::string& sample, const std::string& label) {
  const std::string command = "python '" + helper + "' " + sample + " " + label;
  FILE* pipe = popen(command.c_str(), "r");
  if (!pipe) fail("Cannot run " + command);
  std::string output;
  char buffer[128];
  while (fgets(buffer, sizeof buffer, pipe))
    output += buffer;
  if (pclose(pipe) != 0) fail("The weight helper failed: " + command);
  try {
    return std::stof(output);
  } catch (const std::exception&) {
    fail("The weight helper printed no number: " + command);
  }
}

// ---------------------------------------------------------------- Configuration

// One run of the program, written to one output file
struct Config {
  const Channel* channel = nullptr;
  std::string year;
  const NtracksMode* mode = nullptr;
  int btags = -1;    // -1 keeps every event, 1 only b-tagged ones, 0 only untagged ones
  int bquarks = -1;  // Same, for MC events with a generated b hadron
  bool mc = false;
  bool only20pc = false;
  int minNpu = defaultMinNpu;
  int maxNpu = defaultMaxNpu;
  std::string outDir;
  std::string weightHelper;
};

// For example 2v_from_jets_run2_5track_btags_ULV30Lepm.root
std::string outputName(const Config& cfg) {
  std::vector<std::string> parts;
  if (cfg.btags >= 0) parts.push_back(cfg.btags ? "btags" : "nobtags");
  if (cfg.bquarks >= 0) parts.push_back(cfg.bquarks ? "bquarks" : "nobquarks");
  if (cfg.minNpu != defaultMinNpu || cfg.maxNpu != defaultMaxNpu) parts.push_back("npu" + std::to_string(cfg.minNpu) + "to" + std::to_string(cfg.maxNpu));
  std::string selection = parts.empty() ? "default" : parts[0];
  for (size_t i = 1; i < parts.size(); ++i)
    selection += "_" + parts[i];
  return "2v_from_jets_" + cfg.year + "_" + std::to_string(cfg.mode->code) + "track_" + selection + "_" + cfg.channel->label + ".root";
}

// An input file with its weight and b-tag threshold
struct Sample {
  std::string path;
  float weight;
  float bdiscCut;
};

std::vector<Sample> sampleList(const Config& cfg) {
  const Channel& ch = *cfg.channel;
  const std::string dir = minitreeBase + (cfg.mc ? ch.mcDir : cfg.only20pc ? ch.data20pcDir : ch.dataDir);
  std::vector<Sample> samples;
  for (const std::string& year : yearParts.at(cfg.year))
    for (const SampleSet& set : sampleSets) {
      if (set.channel != ch.name || set.mc != cfg.mc || std::find(set.years.begin(), set.years.end(), year) == set.years.end()) continue;
      for (std::string name : expandNames(set.names)) {
        name += cfg.mc ? "_" + year : cfg.only20pc ? ch.data20pcSuffix : "";
        samples.push_back({dir + "/" + name + ".root", cfg.mc ? mcWeight(cfg.weightHelper, name, ch.label) : 1, bdiscCut(year)});
      }
    }
  return samples;
}

// Trees chained per input file: the 4-track and >= 5-track 1V trees always, the 3-track tree in every mode but 5x5 (so 4x4 and 4x5 pool 3-track DVs too), and the mode's exact-count 2V tree
std::vector<std::string> treeNames(const NtracksMode& mode) {
  std::vector<std::string> trees;
  if (mode.code != 5) trees.push_back("mfvMiniTreeNtk3/t");
  trees.push_back("mfvMiniTreeNtk4/t");
  trees.push_back("mfvMiniTree/t");
  if (!mode.extraTree.empty()) trees.push_back(mode.extraTree);
  return trees;
}

// ---------------------------------------------------------------- Histograms

struct Histos {
  std::map<std::string, TH1*> byName;
  std::vector<TH1*> writeOrder;
  TH1* operator[](const std::string& name) const { return byName.at(name); }
  TH2* twoD(const std::string& name) const { return static_cast<TH2*>(byName.at(name)); }
};

// Books every histogram of histogramSpecs, each with weighted errors
Histos bookHistograms() {
  TH1::SetDefaultSumw2();
  Histos h;
  for (const HistogramSpec& s : histogramSpecs) {
    if (s.type == "again") {
      h.writeOrder.push_back(h[s.name]);
      continue;
    }
    TH1* hist = nullptr;
    if (s.type == "TH1D")
      hist = new TH1D(s.name, s.title, s.nx, s.xlo, s.xhi);
    else if (s.type == "TH1F")
      hist = new TH1F(s.name, s.title, s.nx, s.xlo, s.xhi);
    else if (s.type == "TH2D")
      hist = new TH2D(s.name, s.title, s.nx, s.xlo, s.xhi, s.ny, s.ylo, s.yhi);
    else if (s.type == "TH2F")
      hist = new TH2F(s.name, s.title, s.nx, s.xlo, s.xhi, s.ny, s.ylo, s.yhi);
    else
      fail("Unknown histogram type " + s.type + " for " + s.name);
    h.byName[s.name] = hist;
    h.writeOrder.push_back(hist);
  }
  return h;
}

// ---------------------------------------------------------------- Reading the 1V pool

// One accepted 1V DV with what pairing and revertexing need
struct VertexRecord {
  double dbv;                    // Distance from the beamspot in xy
  double x, y, z;                // Position relative to the PV
  double weight;
  std::array<double, 3> bs, pv;  // Beamspot, and PV relative to the beamspot
  int category;
  reco::TrackCollection tracks;
};

// Every accepted 1V DV and, per category, the indices of all of them, the indices of those with >= 5 tracks (5x5 only), and how many DVs have each track count
struct VertexPool {
  std::vector<VertexRecord> records;
  std::vector<int> all[nCategories], fivePlus[nCategories];
  std::map<size_t, size_t> ntracksCount[nCategories];
};

// b-tagged events first, then untagged ones, each split at npv 20, 30 and 40
int category(bool btagged, int npv) { return (btagged ? 0 : nNpvBins) + (npv <= 20 ? 0 : npv <= 30 ? 1 : npv <= 40 ? 2 : 3); }

// Track-only sum pT and invariant mass of one DV
struct TrackSums {
  double sumPt, mass;
};
TrackSums trackSums(const std::vector<double>* px, const std::vector<double>* py, const std::vector<double>* pz, int n, double pionMass) {
  double sumPt = 0, sumPx = 0, sumPy = 0, sumPz = 0, sumE = 0;
  for (int k = 0; k < n; ++k) {
    const double x = px->at(k), y = py->at(k), z = pz->at(k);
    sumPt += sqrt(x * x + y * y);
    sumPx += x;
    sumPy += y;
    sumPz += z;
    sumE += sqrt(x * x + y * y + z * z + pionMass * pionMass);
  }
  return {sumPt, sqrt(sumE * sumE - sumPx * sumPx - sumPy * sumPy - sumPz * sumPz)};
}

// The pool record of a 1V event's DV, with its tracks rebuilt from the MiniTree
VertexRecord makeRecord(const mfv::MiniNtuple& nt, float dbv, float w, bool btagged) {
  VertexRecord r{dbv, nt.x0 - nt.pvx, nt.y0 - nt.pvy, nt.z0 - nt.pvz, w, {nt.bsx, nt.bsy, nt.bsz}, {nt.pvx, nt.pvy, nt.pvz}, category(btagged, nt.npv), {}};
  for (int k = 0; k < nt.ntk0; ++k) {
    // The sign of qchi2 is the charge; signbit also reads -0.0 as negative
    const int charge = std::signbit(nt.p_tk0_qchi2->at(k)) ? -1 : 1;
    const reco::TrackBase::Point referencePoint(nt.p_tk0_vx->at(k), nt.p_tk0_vy->at(k), nt.p_tk0_vz->at(k));
    const math::XYZVector momentum(nt.p_tk0_px->at(k), nt.p_tk0_py->at(k), nt.p_tk0_pz->at(k));
    r.tracks.push_back(reco::Track(fabs(nt.p_tk0_qchi2->at(k)), nt.p_tk0_ndof->at(k), referencePoint, momentum, charge, nt.p_tk0_cov->at(k)));
  }
  return r;
}

// The 1V histograms of a pooled DV
void fillOneVertexHistograms(const mfv::MiniNtuple& nt, float dbv, float w, const NtracksMode& mode, Histos& h) {
  const float dbvPv = sqrt((nt.x0 - nt.pvx) * (nt.x0 - nt.pvx) + (nt.y0 - nt.pvy) * (nt.y0 - nt.pvy));
  h["h_1v_dbv"]->Fill(dbv, w);
  h["h_1v_bs2derr"]->Fill(nt.bs2derr0, w);
  h["h_1v_rescale_bs2derr"]->Fill(nt.rescale_bs2derr0, w);
  h["h_1v__w"]->Fill(nt.weight);
  h["h_1v_z"]->Fill(nt.z0, w);
  h["h_1v_dz"]->Fill(nt.z0 - nt.pvz, w);
  h["h_1v_dpvsv"]->Fill(sqrt((nt.x0 - nt.pvx) * (nt.x0 - nt.pvx) + (nt.y0 - nt.pvy) * (nt.y0 - nt.pvy) + (nt.z0 - nt.pvz) * (nt.z0 - nt.pvz)), w);
  h.twoD("h_1v_xy")->Fill(nt.x0, nt.y0, w);
  h.twoD("h_1v_dbv_bs2derr")->Fill(dbv, nt.bs2derr0, w);
  h["h_1v_costh2_onlytks0"]->Fill(nt.costhtkonlymombs0, w);
  h["h_1v_costh20"]->Fill(nt.costhtksjetsntkmombs0, w);
  if (nt.ntk0 == mode.ntk0) h["h_1v_dbv0"]->Fill(dbvPv, w);
  if (nt.ntk0 == mode.ntk1) h["h_1v_dbv1"]->Fill(dbvPv, w);
  h["h_1v_phiv"]->Fill(atan2(nt.y0, nt.x0), w);
  h["h_1v_npu"]->Fill(nt.npu, w);
  h["h_1v_npv"]->Fill(nt.npv, w);
  h["h_1v_njets"]->Fill(nt.njets, w);
  h["h_1v_ht40"]->Fill(nt.ht(40.), w);
  double dphijvMin = M_PI;
  for (int k = 0; k < nt.njets; ++k) {
    const double dphijv = TVector2::Phi_mpi_pi(atan2(nt.y0, nt.x0) - nt.jet_phi[k]);
    h["h_1v_phij"]->Fill(nt.jet_phi[k], w);
    h["h_1v_dphijv"]->Fill(dphijv, w);
    h["h_1v_dphijvpt"]->Fill(dphijv, w * (nt.jet_pt[k] / nt.ht(0.)));
    if (fabs(dphijv) < dphijvMin) dphijvMin = fabs(dphijv);
    for (int l = k + 1; l < nt.njets; ++l)
      h["h_1v_dphijj"]->Fill(TVector2::Phi_mpi_pi(nt.jet_phi[k] - nt.jet_phi[l]), w);
  }
  h["h_1v_dphijvmin"]->Fill(dphijvMin, w);
}

// Pools a 1V event's DV when it passes the track cuts, and fills the 1V histograms
void addOneVertexEvent(const mfv::MiniNtuple& nt, float w, bool btagged, const Config& cfg, VertexPool& pool, Histos& h) {
  const TrackSums sums = trackSums(nt.p_tk0_px, nt.p_tk0_py, nt.p_tk0_pz, nt.ntk0, pionMass1v);
  if (sums.sumPt < minTrackSumPt || sums.mass < minTrackMass) return;
  const float dbv = sqrt(nt.x0 * nt.x0 + nt.y0 * nt.y0);
  VertexRecord r = makeRecord(nt, dbv, w, btagged);
  const int index = pool.records.size();
  pool.all[r.category].push_back(index);
  if (cfg.mode->code == 5 && r.tracks.size() >= 5) pool.fivePlus[r.category].push_back(index);
  ++pool.ntracksCount[r.category][r.tracks.size()];
  pool.records.push_back(std::move(r));
  fillOneVertexHistograms(nt, dbv, w, *cfg.mode, h);
}

// Fills the observed 2V histograms of an event in the mode's 2V region. Azimuths are measured from the beamspot.
void fillTwoVertexEvent(const mfv::MiniNtuple& nt, float w, Histos& h) {
  const TrackSums sums0 = trackSums(nt.p_tk0_px, nt.p_tk0_py, nt.p_tk0_pz, nt.ntk0, pionMass2v);
  const TrackSums sums1 = trackSums(nt.p_tk1_px, nt.p_tk1_py, nt.p_tk1_pz, nt.ntk1, pionMass2v);
  if (sums0.sumPt < minTrackSumPt || sums1.sumPt < minTrackSumPt) return;
  if (sums0.mass < minTrackMass || sums1.mass < minTrackMass) return;
  const double dvvMax = dvvNbins * dvvBinWidth - 0.5 * dvvBinWidth;
  const double dbv0 = sqrt(nt.x0 * nt.x0 + nt.y0 * nt.y0);
  const double dbv1 = sqrt(nt.x1 * nt.x1 + nt.y1 * nt.y1);
  double dvv = sqrt((nt.x0 - nt.x1) * (nt.x0 - nt.x1) + (nt.y0 - nt.y1) * (nt.y0 - nt.y1));
  double dvv3D = sqrt((nt.x0 - nt.x1) * (nt.x0 - nt.x1) + (nt.y0 - nt.y1) * (nt.y0 - nt.y1) + (nt.z0 - nt.z1) * (nt.z0 - nt.z1));
  if (dvv > dvvMax) dvv = dvvMax;
  if (dvv3D > dvvMax) dvv3D = dvvMax;
  const double dphi = TVector2::Phi_mpi_pi(atan2(nt.y0, nt.x0) - atan2(nt.y1, nt.x1));
  h["h_2v_dbv"]->Fill(dbv0, w);
  h["h_2v_dbv"]->Fill(dbv1, w);
  h.twoD("h_2v_dbv1_dbv0")->Fill(dbv0, dbv1, w);
  h["h_2v_dvv"]->Fill(dvv, w);
  h["h_2v_dvv3D"]->Fill(dvv3D, w);
  h["h_2v_sumdbv"]->Fill(dbv0 + dbv1, w);
  h["h_2v_dphivv"]->Fill(dphi, w);
  h["h_2v_absdphivv"]->Fill(fabs(dphi), w);
  h["h_2v_npu"]->Fill(nt.npu, w);
  h["h_2v_npv"]->Fill(nt.npv, w);
}

// Reads every input file of the configuration, fills the 1V and 2V histograms and returns the 1V pool
VertexPool readInputs(const Config& cfg, Histos& h) {
  VertexPool pool;
  for (const Sample& sample : sampleList(cfg)) {
    std::cout << sample.path << std::endl;
    mfv::MiniNtuple nt;
    TFile* file = TFile::Open(sample.path.c_str());
    if (!file || !file->IsOpen()) fail("Cannot open input file " + sample.path);
    TChain* chain = new TChain("t");
    for (const std::string& tree : treeNames(*cfg.mode))
      chain->Add((sample.path + "/" + tree).c_str());
    mfv::read_from_tree(chain, nt);

    for (int j = 0, je = chain->GetEntries(); j < je; ++j) {
      if (chain->LoadTree(j) < 0) break;
      if (chain->GetEntry(j) <= 0) continue;
      // Blinding: in data, events with two >= 5-track DVs are skipped before anything is filled
      if (!cfg.mc && nt.nvtx >= 2 && nt.ntk0 >= 5 && nt.ntk1 >= 5) continue;
      // gen_flavor_code is 2 for events with a generated b hadron (1 for a c hadron only, 0 for neither)
      if ((cfg.bquarks == 0 && nt.gen_flavor_code == 2) || (cfg.bquarks == 1 && nt.gen_flavor_code != 2)) continue;
      // DeepJet tags at the year's tight working point; the -1 pT threshold counts every jet
      const bool btagged = nt.nbtags_old(sample.bdiscCut, -1) >= 1;
      if ((cfg.btags == 0 && btagged) || (cfg.btags == 1 && !btagged)) continue;
      if (nt.npu < cfg.minNpu || nt.npu > cfg.maxNpu) continue;
      const float w = sample.weight * nt.weight;
      if (nt.nvtx == 1) addOneVertexEvent(nt, w, btagged, cfg, pool, h);
      // Kept for the bit-identical check (the observed 5x5 region takes exactly 5 tracks per DV)
      if (nt.nvtx >= 2 && nt.ntk0 == cfg.mode->ntk0 && nt.ntk1 == cfg.mode->ntk1) fillTwoVertexEvent(nt, w, h);
    }
    delete chain;
    file->Close();
    delete file;
  }

  // Negative MC weights can leave negative bins
  for (const char* name : {"h_1v_dbv0", "h_1v_dbv1"})
    for (int bin = 0; bin <= h[name]->GetNbinsX() + 1; ++bin)
      if (h[name]->GetBinContent(bin) < 0) h[name]->SetBinContent(bin, 0);
  return pool;
}

// ---------------------------------------------------------------- Vertexer port
// The JMTucker Vertexer steps on one constructed event, under Kamui's step names: two-track seeds, sharedTracks and mergeNearby; zRefit and sharedJets are skipped (revertexPair). The control flow is JMTucker's, as in Kamui's DVProducer, so the vertexer bugs of Kamui's Bugs/ folder marked below apply here too.

typedef std::set<reco::TrackRef> TrackSet;
typedef std::vector<reco::Vertex>::iterator VertexIter;

// The fitter of every seed and refit: KalmanVertexFitter's default settings (maxDistance 0.01, at most 10 iterations), with smoothing
const KalmanVertexFitter& fitter() {
  static const KalmanVertexFitter instance(true);
  return instance;
}

TrackSet vertexTrackSet(const reco::Vertex& v) {
  TrackSet result;
  for (auto it = v.tracks_begin(), ite = v.tracks_end(); it != ite; ++it)
    result.insert(it->castTo<reco::TrackRef>());
  return result;
}

bool isTrackSubset(const TrackSet& a, const TrackSet& b) {
  const TrackSet& smaller = a.size() <= b.size() ? a : b;
  const TrackSet& bigger = a.size() <= b.size() ? b : a;
  for (auto tk : smaller)
    if (bigger.count(tk) < 1) return false;
  return true;
}

// Track keys index the constructed event's track collection, which is also the order of seedTracks
std::vector<reco::TransientTrack> transientTracks(const TrackSet& tracks, const std::vector<reco::TransientTrack>& seedTracks) {
  std::vector<reco::TransientTrack> ttks;
  for (const reco::TrackRef& tk : tracks)
    ttks.push_back(seedTracks.at(tk.key()));
  return ttks;
}

// False for fewer than 2 tracks or chi2/dof above the cut. Like JMTucker's kv_reco_dropin it never checks validity, so a failed fit comes back as an invalid DV, and a negative chi2 passes (Bugs/jmtucker/adapted/negativeChi2PassesCuts.md).
bool fitVertex(const std::vector<reco::TransientTrack>& ttks, reco::Vertex& out) {
  if (ttks.size() < 2) return false;
  const TransientVertex tv = fitter().vertex(ttks);
  if (tv.normalisedChiSquared() > maxChi2PerDof) return false;
  out = reco::Vertex(tv);
  return true;
}

// Every pair of tracks whose fit is valid with chi2/dof below the cut. The cut is strict here and inclusive in fitVertex.
reco::VertexCollection seedVertices(const std::vector<reco::TransientTrack>& seedTracks) {
  reco::VertexCollection vertices;
  for (size_t i = 0; i < seedTracks.size(); ++i)
    for (size_t j = i + 1; j < seedTracks.size(); ++j) {
      const TransientVertex seed = fitter().vertex(std::vector<reco::TransientTrack>{seedTracks[i], seedTracks[j]});
      if (seed.isValid() && seed.normalisedChiSquared() < maxChi2PerDof) vertices.push_back(reco::Vertex(seed));
    }
  return vertices;
}

// sharedTracks: two DVs that share a track merge when they are close. Otherwise the track leaves the DV it fits worse, and also any DV it is too far from, so it can leave both. Any change restarts the scan.
void resolveSharedTracks(reco::VertexCollection& vertices, const std::vector<reco::TransientTrack>& seedTracks) {
  const VertexDistance3D vertexDist3d;
  VertexIter v[2];
  for (v[0] = vertices.begin(); v[0] != vertices.end(); ++v[0]) {
    TrackSet tracks[2];
    tracks[0] = vertexTrackSet(*v[0]);
    if (tracks[0].size() < 2) {
      // Steps before begin() when v[0] is the first DV
      v[0] = vertices.erase(v[0]) - 1;
      continue;
    }

    bool duplicate = false, merge = false, refit = false;
    TrackSet toRemove[2];
    for (v[1] = v[0] + 1; v[1] != vertices.end(); ++v[1]) {
      tracks[1] = vertexTrackSet(*v[1]);
      if (tracks[1].size() < 2) {
        v[1] = vertices.erase(v[1]) - 1;
        continue;
      }
      if (isTrackSubset(tracks[0], tracks[1])) {
        duplicate = true;
        break;
      }

      // Only the first shared track is arbitrated per pass
      const auto shared = std::find_if(tracks[0].begin(), tracks[0].end(), [&](const reco::TrackRef& tk) { return tracks[1].count(tk) > 0; });
      if (shared == tracks[0].end()) continue;
      if (vertexDist3d.distance(*v[0], *v[1]).significance() < sharedTracksMergeBelowSigma)
        merge = true;
      else
        refit = true;

      const reco::TransientTrack& ttk = seedTracks.at(shared->key());
      const std::pair<bool, Measurement1D> dist0 = IPTools::absoluteImpactParameter3D(ttk, *v[0]);
      const std::pair<bool, Measurement1D> dist1 = IPTools::absoluteImpactParameter3D(ttk, *v[1]);
      bool removeFrom0 = !(dist0.first && dist0.second.significance() < sharedTracksKeepBelowSigma);
      bool removeFrom1 = !(dist1.first && dist1.second.significance() < sharedTracksKeepBelowSigma);
      if (dist0.second.significance() < sharedTracksTieBelowSigma && dist1.second.significance() < sharedTracksTieBelowSigma) {
        if (tracks[0].size() > tracks[1].size())
          removeFrom1 = true;
        else
          removeFrom0 = true;
      } else if (dist0.second.significance() < dist1.second.significance())
        removeFrom1 = true;
      else
        removeFrom0 = true;
      if (removeFrom0) toRemove[0].insert(*shared);
      if (removeFrom1) toRemove[1].insert(*shared);
      break;
    }

    // Erases the second DV even when it holds more tracks
    if (duplicate)
      vertices.erase(v[1]);
    else if (merge) {
      TrackSet toFit(tracks[0]);
      toFit.insert(tracks[1].begin(), tracks[1].end());
      reco::Vertex merged;
      if (fitVertex(transientTracks(toFit, seedTracks), merged) && vertexTrackSet(merged) == toFit) {
        vertices.erase(v[1]);
        *v[0] = merged;
      } else
        refit = true;
    }

    if (refit) {
      bool erase[2] = {false, false};
      for (int i = 0; i < 2; ++i) {
        if (toRemove[i].empty()) continue;
        TrackSet kept;
        for (auto tk : tracks[i])
          if (toRemove[i].count(tk) == 0) kept.insert(tk);
        reco::Vertex refitted;
        if (fitVertex(transientTracks(kept, seedTracks), refitted))
          *v[i] = refitted;
        else
          erase[i] = true;
      }
      if (erase[1]) vertices.erase(v[1]);
      if (erase[0]) vertices.erase(v[0]);
    }

    // Restarts the scan from before begin()
    if (duplicate || merge || refit) v[0] = vertices.begin() - 1;
  }
}

// mergeNearby: merges two DVs at about the same azimuth, close in xy and away from the beamspot, when the merged fit keeps all their tracks. tracks[0] keeps the first DV's set from before any merge in the inner loop, as in JMTucker (Bugs/jmtucker/adapted/mergeNearbyStaleTrackList.md).
void mergeNearby(reco::VertexCollection& vertices, const std::vector<reco::TransientTrack>& seedTracks, const reco::Vertex& beamspot) {
  const VertexDistanceXY vertexDist2d;
  VertexIter v[2];
  for (v[0] = vertices.begin(); v[0] != vertices.end(); ++v[0]) {
    TrackSet tracks[2];
    tracks[0] = vertexTrackSet(*v[0]);
    bool merged = false;
    for (v[1] = v[0] + 1; v[1] != vertices.end(); ++v[1]) {
      if (v[0]->nTracks() < 2 || v[1]->nTracks() < 2) continue;
      tracks[1] = vertexTrackSet(*v[1]);
      const double dist2d = vertexDist2d.distance(*v[0], *v[1]).value();
      const double dbv0 = vertexDist2d.distance(*v[0], beamspot).value();
      const double dbv1 = vertexDist2d.distance(*v[1], beamspot).value();
      const double phi0 = atan2(v[0]->y() - beamspot.y(), v[0]->x() - beamspot.x());
      const double phi1 = atan2(v[1]->y() - beamspot.y(), v[1]->x() - beamspot.x());
      if (!(fabs(reco::deltaPhi(phi0, phi1)) < mergeNearbyDeltaPhiBelow && dist2d < mergeNearbyDistance2dBelow && dbv0 > mergeNearbyDbvAbove && dbv1 > mergeNearbyDbvAbove)) continue;

      TrackSet toFit(tracks[0]);
      toFit.insert(tracks[1].begin(), tracks[1].end());
      reco::Vertex mergedVertex;
      if (fitVertex(transientTracks(toFit, seedTracks), mergedVertex) && vertexTrackSet(mergedVertex) == toFit) {
        merged = true;
        v[1] = vertices.erase(v[1]) - 1;
        *v[0] = mergedVertex;
      }
    }
    // Restarts the scan from before begin()
    if (merged) v[0] = vertices.begin() - 1;
  }
}

// What came back from revertexing one constructed event
struct RevertexedPair {
  std::vector<int> ntracks;
  std::vector<reco::Vertex::Point> positions;
};

// Builds the constructed event and revertexes it. The partner's tracks move rigidly so that its PV lands on the anchor's PV; momenta and covariances are unchanged.
RevertexedPair revertexPair(const VertexRecord& v0, const VertexRecord& v1) {
  static const UniformMagneticField field(magneticField);
  reco::TrackCollection tracks = v0.tracks;
  for (const reco::Track& t : v1.tracks) {
    // Written term by term as in the original: computing the shift once changes the last bits of the positions
    const reco::TrackBase::Point shifted(t.vx() - (v1.pv[0] + v1.bs[0]) + (v0.pv[0] + v0.bs[0]), t.vy() - (v1.pv[1] + v1.bs[1]) + (v0.pv[1] + v0.bs[1]), t.vz() - (v1.pv[2] + v1.bs[2]) + (v0.pv[2] + v0.bs[2]));
    tracks.push_back(reco::Track(t.chi2(), t.ndof(), shifted, t.momentum(), t.charge(), t.covariance()));
  }
  std::vector<reco::TransientTrack> seedTracks;
  for (size_t k = 0; k < tracks.size(); ++k)
    seedTracks.push_back(reco::TransientTrack(reco::TrackRef(&tracks, k), &field));

  // The anchor's beamspot stands in for the constructed event's. Only distances from it are used, so it carries no uncertainty.
  const reco::Vertex beamspot(reco::Vertex::Point(v0.bs[0], v0.bs[1], v0.bs[2]), reco::Vertex::Error());

  reco::VertexCollection vertices = seedVertices(seedTracks);
  resolveSharedTracks(vertices, seedTracks);
  // Kept for the bit-identical check: Bugs/backgroundTemplate/templateZRefitSkipped.md (zRefit and its chi2/dof cleanup are skipped) and Bugs/backgroundTemplate/templateSharedJetsSkipped.md
  mergeNearby(vertices, seedTracks, beamspot);

  RevertexedPair out;
  for (const reco::Vertex& v : vertices) {
    out.ntracks.push_back(v.tracksSize());
    out.positions.push_back(v.position());
  }
  return out;
}

// ---------------------------------------------------------------- Pairing and filling

// The two pairing passes: the partner is any DV of the anchor's category, or one with >= 5 tracks (5x5 only)
enum class Partners { any, fivePlus };

// Whether a revertexed pair enters the template of a mode
bool passesTemplate(int code, const std::vector<int>& n) {
  // Kept for the bit-identical check: Bugs/backgroundTemplate/templateAcceptanceNoTightCuts.md (exactly two output DVs, no tight DV cuts)
  if (n.size() != 2) return false;
  if (code == 5) return n[0] >= 5 && n[1] >= 5;
  // Kept for the bit-identical check: Bugs/backgroundTemplate/templateSidebandAcceptance.md (3x5 and 4x5 accept >= 6-track DVs, and through the last line 3x4, 3x5 and 4x5 accept 7x7, 8x8 and 9x9)
  if (code == 9 && (n[0] == 4 || n[1] == 4) && (n[0] >= 5 || n[1] >= 5)) return true;
  if (code == 8 && (n[0] == 3 || n[1] == 3) && (n[0] >= 5 || n[1] >= 5)) return true;
  if (code == 7 && n[0] + n[1] == 7 && n[0] != n[1] && n[0] > 2 && n[1] > 2) return true;
  return n[0] == code && n[1] == code;
}

// |dPhi| of the two input DVs, with azimuths measured from each event's PV
// Kept for the bit-identical check (the observed h_2v_absdphivv measures them from the beamspot)
double absDeltaPhi(const VertexRecord& v0, const VertexRecord& v1) {
  const double phi0 = std::atan2(v0.y, v0.x), phi1 = std::atan2(v1.y, v1.x);
  if (M_PI < phi1 - phi0) return 2 * M_PI - (phi1 - phi0);
  if (-M_PI > phi1 - phi0) return 2 * M_PI + (phi1 - phi0);
  return fabs(phi1 - phi0);
}

void fillPair(const VertexRecord& v0, const VertexRecord& v1, const RevertexedPair& out, int code, Histos& h) {
  // b-composition weight: f2/f1 for b-tagged anchors and (1 - f2)/(1 - f1) for untagged ones, with the placeholders f2 = 0.99 and f1 = 0.80
  // Kept for the bit-identical check: Bugs/backgroundTemplate/templateBtagWeightIntegerDivision.md (integer division gives 1 and 0)
  const double btagWeight = v0.category < nNpvBins ? 99 / 80 : 1 / 20;
  // Kept for the bit-identical check (in MC, uniform partner draws times this product weight each category by its mean event weight)
  const double w = btagWeight * (v0.weight * v1.weight);
  const double sumDbv = v0.dbv + v1.dbv;
  const double dvv3D = sqrt((v0.x - v1.x) * (v0.x - v1.x) + (v0.y - v1.y) * (v0.y - v1.y) + (v0.z - v1.z) * (v0.z - v1.z));

  // Track counts of the output DVs as returned when there are two, otherwise the two largest (0 when missing)
  std::vector<int> n = out.ntracks;
  if (n.size() != 2) std::sort(n.begin(), n.end(), std::greater<int>());
  const int ntrk0 = n.size() > 0 ? n[0] : 0, ntrk1 = n.size() > 1 ? n[1] : 0;

  // Every trial fills these, passing or not
  h.twoD("h_c1v_ntrk0_ntrk1")->Fill(ntrk0, ntrk1, w);
  h["h_c1v_dvv3D_w_errorbars"]->Fill(dvv3D, w);
  h["h_c1v_sumdbv_w_errorbars"]->Fill(sumDbv, w);
  if (!passesTemplate(code, out.ntracks)) return;
  const reco::Vertex::Point &p0 = out.positions[0], &p1 = out.positions[1];
  h["h_c1v_dvv3D_revertexed_w_errorbars"]->Fill(sqrt((p0.x() - p1.x()) * (p0.x() - p1.x()) + (p0.y() - p1.y()) * (p0.y() - p1.y()) + (p0.z() - p1.z()) * (p0.z() - p1.z())), w);
  h["h_c1v_sumdbv_revertexed_w_errorbars"]->Fill(sumDbv, w);
  h["h_c1v_absdphivv_revertexed_w_errorbars"]->Fill(absDeltaPhi(v0, v1), w);
}

// Draws the partner of anchor i from its category. Partners with the anchor's exact dBV are redrawn, which excludes the anchor itself.
int drawPartner(std::mt19937& gen, const VertexPool& pool, size_t i, Partners partners, const NtracksMode& mode) {
  const VertexRecord& v0 = pool.records[i];
  const std::vector<int>& candidates = partners == Partners::any ? pool.all[v0.category] : pool.fivePlus[v0.category];
  // Kept for the bit-identical check (for the b-tagged, npv <= 20 category the >= 5-track pass checks the size of the list of all DVs)
  const size_t guardSize = partners == Partners::fivePlus && v0.category == 0 ? pool.all[0].size() : candidates.size();
  // Kept for the bit-identical check: Bugs/backgroundTemplate/templateSameNtracksVetoOneCategory.md (in 3x4, 3x5 and 4x5 only the b-tagged, npv <= 20 category rejects partners with the anchor's track count)
  const bool vetoSameNtracks = partners == Partners::any && v0.category == 0 && mode.ntk0 != mode.ntk1;
  const auto acceptable = [&](int c) {
    const VertexRecord& p = pool.records[c];
    return v0.dbv != p.dbv && !(vetoSameNtracks && v0.tracks.size() == p.tracks.size());
  };
  std::uniform_int_distribution<> dist(0, candidates.size() - 1);
  // Kept for the bit-identical check (with fewer than two candidates the anchor can become its own partner)
  if (guardSize < 2) return candidates[dist(gen)];
  // Where no candidate is acceptable the original redraws forever, so stop with an error. These checks draw no random numbers.
  if (candidates.size() == 1 && !acceptable(candidates[0])) fail("The only >= 5-track DV of the b-tagged, npv <= 20 category has no partner, and the original would redraw forever. Use a larger sample.");
  if (vetoSameNtracks && pool.ntracksCount[v0.category].at(v0.tracks.size()) == candidates.size()) fail("Every DV of the b-tagged, npv <= 20 category has " + std::to_string(v0.tracks.size()) + " tracks, and the original would redraw forever (Bugs/backgroundTemplate/templateSameNtracksVetoOneCategory.md). Use a larger sample.");
  int k;
  do
    k = dist(gen);
  while (!acceptable(candidates[k]));
  return candidates[k];
}

// One pass over the pool: every anchor gets one partner, and the constructed event is revertexed and filled
void pairingLoop(Partners partners, const VertexPool& pool, const NtracksMode& mode, Histos& h) {
  std::mt19937 gen(partners == Partners::any ? anyPartnerSeed : fivePlusPartnerSeed);
  for (size_t i = 0; i < pool.records.size(); ++i) {
    const VertexRecord& v0 = pool.records[i];
    if (mode.code == 5 && v0.tracks.size() < 5) continue;
    // Unused draw, kept because it advances gen
    if (partners == Partners::any) std::uniform_int_distribution<>(0, pool.records.size() - 1)(gen);
    const VertexRecord& v1 = pool.records[drawPartner(gen, pool, i, partners, mode)];
    fillPair(v0, v1, revertexPair(v0, v1), mode.code, h);
  }
}

// ---------------------------------------------------------------- Output

// Overlays the observed 2V sumdBV and the constructed one, each scaled to unit area. Draw keeps pointers, and the scaling runs after the histograms are written, so only the copies stored in the canvas come out normalized.
// Kept for the bit-identical check (the constructed curve holds every trial, before the template test)
TCanvas* sumDbvCanvas(const Histos& h) {
  TCanvas* canvas = new TCanvas("c_sumdbv_w_errorbars", "c_sumdbv_w_errorbars", 700, 700);
  TLegend* legend = new TLegend(0.35, 0.75, 0.85, 0.85);
  h["h_2v_sumdbv"]->SetTitle(";#Sigmad_{BV} (cm);events");
  struct Curve {
    const char* name;
    Color_t color;
    const char* drawOption;
    const char* label;
  };
  for (const Curve& curve : {Curve{"h_2v_sumdbv", kBlue, "", "two-vertex events"}, Curve{"h_c1v_sumdbv_w_errorbars", kRed, "sames", "constructed from only-one-vertex events"}}) {
    TH1* hist = h[curve.name];
    hist->SetLineColor(curve.color);
    hist->SetLineWidth(3);
    hist->Scale(1. / hist->Integral());
    hist->SetStats(0);
    hist->Draw(curve.drawOption);
    legend->AddEntry(hist, curve.label);
  }
  legend->SetFillColor(0);
  legend->Draw();
  canvas->SetTickx();
  canvas->SetTicky();
  return canvas;
}

void writeOutputs(const std::string& path, Histos& h) {
  TFile* out = TFile::Open(path.c_str(), "recreate");
  if (!out || !out->IsOpen()) fail("Cannot write " + path);
  for (TH1* hist : h.writeOrder)
    hist->Write();
  TCanvas* canvas = sumDbvCanvas(h);
  canvas->Write();
  // Kept for the bit-identical check: a flat dPhi function that nothing here or downstream uses. It is made with new, as in the original, because ROOT writes into the file whether an object was made with new.
  TF1* flatDphi = new TF1("f_dphi", "[1] + [2] + 1.0/[0]", 0, M_PI);
  flatDphi->SetParameters(M_PI, 0.0, 0.0);
  flatDphi->Write();
  out->Close();
  delete out;
  delete flatDphi;
  delete canvas;
}

// cb_vals.csv feeds bquark_fraction.py, with one row per b-tagged or untagged run. Each value is a pair-efficiency sum divided by the number of pooled DVs, and the sum stays 0 since revertexing replaced the efficiencies, so every row reads 0 (NaN for an empty pool).
// Kept for the bit-identical check: Bugs/backgroundTemplate/templateBQuarkFractionUnmeasured.md
void writeCbValues(const std::string& cbDir, const std::string& label, const std::vector<std::pair<std::string, int>>& runs) {
  std::ofstream csv(cbDir + "/cb_vals.csv");
  csv << "variant,cb_val" << std::endl;
  for (const auto& run : runs) {
    TString row = TString::Format("%s, %f", run.first.c_str(), 0.0 / run.second);
    if (!row.Contains("_btags_") && !row.Contains("_nobtags_")) continue;
    row.ReplaceAll("2v_from_jets_", "");
    row.ReplaceAll("_" + TString(label) + ".root", "");
    row.ReplaceAll("_btags", "_cb");
    row.ReplaceAll("_nobtags", "_cbbar");
    row.ReplaceAll("track", "trk");
    row.ReplaceAll(" ", "");
    csv << row << std::endl;
  }
}

// Reads the inputs, pairs and revertexes, and writes one output file. Returns the number of pooled 1V DVs.
int runConfiguration(const Config& cfg, const std::string& fileName) {
  std::cout << "Running " << fileName << std::endl;
  gROOT->cd();
  Histos h = bookHistograms();
  const VertexPool pool = readInputs(cfg, h);
  std::cout << "Pairing " << pool.records.size() << " 1V DVs" << std::endl;
  // Kept for the bit-identical check: Bugs/backgroundTemplate/templateLoopsFixTrialMix.md (the two passes fix the mix of 4x>=5 and >=5x>=5 trials) and Bugs/backgroundTemplate/templateErrorsIgnorePairing.md (one partner per anchor, plain Sumw2 errors)
  pairingLoop(Partners::any, pool, *cfg.mode, h);
  if (cfg.mode->code == 5) pairingLoop(Partners::fivePlus, pool, *cfg.mode, h);
  writeOutputs(cfg.outDir + "/" + fileName, h);
  for (auto& entry : h.byName)
    delete entry.second;
  return pool.records.size();
}

// ---------------------------------------------------------------- Command line

const char* usage = R"(Usage: 2v_from_jets.exe --channel lepton|displacement --outDir DIR [options]

Builds the 2V background template from 1V events. With only --channel and --outDir it runs the production set of the channel: run2, 5x5, and the b-tag selections all, 1 and 0, each into its own file.

For one configuration, for example the lepton 3x3 template over all events:
  2v_from_jets.exe --channel lepton --outDir lepton3x3 --ntracks 3x3 --btags all

Required:
  --channel lepton|displacement  Trigger channel: lepton reads the ULV30Lepm MiniTrees, displacement the ULV30BvetoLHTm ones.
  --outDir DIR                   Folder for the ROOT files and cb_vals/cb_vals.csv, created if missing. File names do not say whether a run read data, 20% data or MC, so give each its own folder.

Options. A comma list runs every value, and the lists run in every combination:
  --year LIST        run2, 20161 (2016 preVFP), 20162 (2016 postVFP), 2017, 2018, or 2017p8 for 2017 and 2018 together. Default run2.
  --ntracks LIST     Track counts of the 2V region the template stands for: 3x3, 4x4, 5x5, 3x4, 3x5 or 4x5, or their file-name codes below. Default 5x5.
  --btags LIST       Events by tight DeepJet b tags: all, 1 for at least one b-tagged jet, 0 for none. Default all,1,0. With 0 the template is empty, since untagged pairs get weight 0 (Kamui Bugs/backgroundTemplate/templateBtagWeightIntegerDivision.md).
  --mc               Read the background MC, weighted by 2v_from_jets_new.py next to the executable. Default data.
  --bquarks all|1|0  With --mc: every event, only those with a generated b hadron (1), or only those without (0). Default all.
  --minNpu N         With --mc: keep events with at least N pileup interactions.
  --maxNpu N         With --mc: keep events with at most N pileup interactions.
  --only20pc         Data only: read the 20% data MiniTrees. The displacement channel has none, so, as in the original, it reads the per-era data files of MiniTree_tag004BvetoLHTm.
  --help             Print this text.
Options also work as --option=value.

Each run writes 2v_from_jets_<year>_<code>track_<selection>_<label>.root, where
  <code>       is 3, 4 or 5 for 3x3, 4x4 or 5x5, and 7, 8 or 9 for 3x4, 3x5 or 4x5
  <selection>  is default when nothing is selected, otherwise btags or nobtags, bquarks or nobquarks, and npu<min>to<max>, joined by underscores
  <label>      is ULV30Lepm or ULV30BvetoLHTm
Every invocation rewrites cb_vals/cb_vals.csv. In data, events with two >= 5-track DVs are skipped (blinding), so the 5x5 h_2v_* histograms are empty.
)";

// The command line: the settings every run shares, and the lists whose every combination runs
struct Options {
  Config base;
  std::vector<std::string> years{"run2"};
  std::vector<const NtracksMode*> modes;  // Default 5x5
  std::vector<int> btags{-1, 1, 0};       // The production set
};

const Channel* findChannel(const std::string& name) {
  std::string known;
  for (const Channel& ch : channels) {
    if (ch.name == name) return &ch;
    known += " " + ch.name;
  }
  usageError("Unknown --channel value " + name + ", known:" + known);
}

const NtracksMode* findMode(const std::string& name) {
  std::string known;
  for (const NtracksMode& mode : ntracksModes) {
    if (mode.name == name || std::to_string(mode.code) == name) return &mode;
    known += " " + mode.name;
  }
  usageError("Unknown --ntracks value " + name + ", known:" + known);
}

// A comma list of distinct values
std::vector<std::string> parseList(const std::string& value, const std::string& option) {
  const std::vector<std::string> parts = split(value, ',');
  std::set<std::string> seen;
  for (const std::string& part : parts)
    if (part.empty() || !seen.insert(part).second) usageError(option + " needs distinct values separated by commas, got " + value);
  if (parts.empty() || value.back() == ',') usageError(option + " needs distinct values separated by commas, got " + value);
  return parts;
}

int parseSelection(const std::string& value, const std::string& option) {
  if (value == "all") return -1;
  if (value != "1" && value != "0") usageError(option + " takes all, 1 or 0, got " + value);
  return value == "1";
}

// A pileup count, stored in one byte
int parseNpu(const std::string& value, const std::string& option) {
  char* end = nullptr;
  const long n = strtol(value.c_str(), &end, 10);
  if (value.empty() || *end != '\0' || n < defaultMinNpu || n > defaultMaxNpu) usageError(option + " needs a whole number from " + std::to_string(defaultMinNpu) + " to " + std::to_string(defaultMaxNpu) + ", got " + value);
  return n;
}

Options parseArguments(int argc, char** argv) {
  if (argc == 1) {
    std::cout << usage;
    exit(0);
  }
  Options opt;
  opt.modes = {findMode("5x5")};
  const std::string exe = argv[0];
  const size_t slash = exe.rfind('/');
  opt.base.weightHelper = (slash == std::string::npos ? std::string(".") : exe.substr(0, slash)) + "/2v_from_jets_new.py";
  const std::set<std::string> takesValue{"--channel", "--year", "--ntracks", "--btags", "--bquarks", "--minNpu", "--maxNpu", "--outDir"};
  bool npuGiven = false;
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i], value;
    const size_t equals = arg.find('=');
    const bool inlineValue = arg.rfind("--", 0) == 0 && equals != std::string::npos;
    if (inlineValue) {
      value = arg.substr(equals + 1);
      arg = arg.substr(0, equals);
    }
    if (arg == "--help" || arg == "-h") {
      std::cout << usage;
      exit(0);
    }
    if (arg == "--mc" || arg == "--only20pc") {
      if (inlineValue) usageError(arg + " takes no value");
      if (arg == "--mc") opt.base.mc = true;
      if (arg == "--only20pc") opt.base.only20pc = true;
      continue;
    }
    if (!takesValue.count(arg)) usageError("Unknown argument " + arg);
    if (!inlineValue) {
      if (i + 1 >= argc || std::string(argv[i + 1]).rfind("--", 0) == 0) usageError(arg + " needs a value");
      value = argv[++i];
    }
    if (arg == "--channel") opt.base.channel = findChannel(value);
    if (arg == "--year") {
      opt.years = parseList(value, arg);
      for (const std::string& year : opt.years)
        if (!yearParts.count(year)) {
          std::string known;
          for (const auto& entry : yearParts)
            known += " " + entry.first;
          usageError("Unknown --year value " + year + ", known:" + known);
        }
    }
    if (arg == "--ntracks") {
      opt.modes.clear();
      for (const std::string& name : parseList(value, arg))
        opt.modes.push_back(findMode(name));
    }
    if (arg == "--btags") {
      opt.btags.clear();
      for (const std::string& selection : parseList(value, arg))
        opt.btags.push_back(parseSelection(selection, arg));
    }
    if (arg == "--bquarks") opt.base.bquarks = parseSelection(value, arg);
    if (arg == "--minNpu") opt.base.minNpu = parseNpu(value, arg);
    if (arg == "--maxNpu") opt.base.maxNpu = parseNpu(value, arg);
    if (arg == "--minNpu" || arg == "--maxNpu") npuGiven = true;
    if (arg == "--outDir") opt.base.outDir = value;
  }

  if (!opt.base.channel) usageError("--channel is required");
  if (opt.base.outDir.empty()) usageError("--outDir is required");
  if (opt.base.bquarks >= 0 && !opt.base.mc) usageError("--bquarks needs --mc, since data has no generated b hadrons");
  if (npuGiven && !opt.base.mc) usageError("--minNpu and --maxNpu need --mc, since data MiniTrees store npu as 0");
  if (opt.base.minNpu > opt.base.maxNpu) usageError("--minNpu is above --maxNpu");
  if (opt.base.only20pc && opt.base.mc) usageError("--only20pc applies to data only");
  if (opt.base.mc && gSystem->AccessPathName(opt.base.weightHelper.c_str())) fail("--mc needs the weight helper " + opt.base.weightHelper);
  return opt;
}

int main(int argc, char** argv) {
  const Options opt = parseArguments(argc, argv);
  const std::string cbDir = opt.base.outDir + "/" + cbValuesDir;
  gSystem->mkdir(cbDir.c_str(), true);
  if (gSystem->AccessPathName(cbDir.c_str())) fail("Cannot create " + cbDir);
  gStyle->SetPadTickX(1);
  gStyle->SetPadTickY(1);

  std::vector<std::pair<std::string, int>> runs;
  for (const std::string& year : opt.years)
    for (const NtracksMode* mode : opt.modes)
      for (int btags : opt.btags) {
        Config cfg = opt.base;
        cfg.year = year;
        cfg.mode = mode;
        cfg.btags = btags;
        const std::string fileName = outputName(cfg);
        runs.push_back({fileName, runConfiguration(cfg, fileName)});
      }
  writeCbValues(cbDir, opt.base.channel->label, runs);
  return 0;
}
