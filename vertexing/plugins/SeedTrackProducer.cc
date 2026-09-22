#include <cmath>
#include <string>
#include <vector>

#include "DataFormats/BeamSpot/interface/BeamSpot.h"
#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/PatCandidates/interface/PackedCandidate.h"
#include "DataFormats/SiPixelDetId/interface/PixelSubdetector.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

class DxyErrScale {
public:
  explicit DxyErrScale(const edm::ParameterSet&);
  double rescaledDxyErr(const reco::Track&) const;

private:
  enum class Form { none, constant, subtractScaledExp, subtractShiftedExp };

  static Form parseForm(const std::string&);

  const Form form_;
  const double barrelMaxAbsEta_;
  const std::vector<double> barrel_;
  const std::vector<double> endcap_;
};

DxyErrScale::Form DxyErrScale::parseForm(const std::string& form) {
  if (form == "none")
    return Form::none;
  if (form == "p0")
    return Form::constant;
  if (form == "p0-p2*exp(-p1*x)")
    return Form::subtractScaledExp;
  if (form == "p0-exp(-p1*x+p2)")
    return Form::subtractShiftedExp;
  throw cms::Exception("SeedTrackProducer") << "unknown dxyErrScale form '" << form << "'";
}

DxyErrScale::DxyErrScale(const edm::ParameterSet& cfg)
    : form_(parseForm(cfg.getParameter<std::string>("form"))),
      barrelMaxAbsEta_(cfg.getParameter<double>("barrelMaxAbsEta")),
      barrel_(cfg.getParameter<std::vector<double>>("barrel")),
      endcap_(cfg.getParameter<std::vector<double>>("endcap")) {
  const size_t nParams = form_ == Form::none ? 0 : form_ == Form::constant ? 1 : 3;
  if (barrel_.size() != nParams || endcap_.size() != nParams)
    throw cms::Exception("SeedTrackProducer") << "dxyErrScale needs " << nParams << " parameters each for barrel and endcap";
}

double DxyErrScale::rescaledDxyErr(const reco::Track& tk) const {
  if (form_ == Form::none)
    return tk.dxyError();

  const std::vector<double>& p = std::fabs(tk.eta()) < barrelMaxAbsEta_ ? barrel_ : endcap_;
  const double x = tk.pt();
  double scale;
  if (form_ == Form::constant)
    scale = p[0];
  else if (form_ == Form::subtractScaledExp)
    scale = p[0] - p[2] * exp(-p[1] * x);
  else
    scale = p[0] - exp(-p[1] * x + p[2]);

  reco::TrackBase::CovarianceMatrix cov = tk.covariance();
  cov(reco::TrackBase::i_dxy, reco::TrackBase::i_dxy) *= pow(scale, 2);
  return reco::Track(tk.chi2(), tk.ndof(), tk.referencePoint(), tk.momentum(), tk.charge(), cov, tk.algo()).dxyError();
}

class SeedTrackProducer : public edm::global::EDProducer<> {
public:
  explicit SeedTrackProducer(const edm::ParameterSet&);
  void produce(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

private:
  const reco::Vertex* firstGoodPv(const reco::VertexCollection&) const;
  bool isSeed(const reco::Track&, const reco::BeamSpot&, const reco::Vertex&) const;

  const edm::EDGetTokenT<pat::PackedCandidateCollection> candidatesToken_;
  const edm::EDGetTokenT<reco::BeamSpot> beamSpotToken_;
  const edm::EDGetTokenT<reco::VertexCollection> primaryVerticesToken_;
  const double pvMinNdof_;
  const double pvMaxAbsZ_;
  const double pvMaxRho_;
  const double minPt_;
  const double minAbsDxyBs_;
  const double maxDxyErr_;
  const double minNSigmaDxyBs_;
  const double minRescaledNSigmaDxyBs_;
  const double minNSigmaDxyPv_;
  const int minHits_;
  const int minPixelHits_;
  const int minPixelLayers_;
  const int minStripLayers_;
  const int maxFirstPixelLayer_;
  const DxyErrScale dxyErrScale_;
};

SeedTrackProducer::SeedTrackProducer(const edm::ParameterSet& cfg)
    : candidatesToken_(consumes(cfg.getParameter<edm::InputTag>("src"))),
      beamSpotToken_(consumes(cfg.getParameter<edm::InputTag>("beamSpot"))),
      primaryVerticesToken_(consumes(cfg.getParameter<edm::InputTag>("primaryVertices"))),
      pvMinNdof_(cfg.getParameter<edm::ParameterSet>("goodPv").getParameter<double>("minNdof")),
      pvMaxAbsZ_(cfg.getParameter<edm::ParameterSet>("goodPv").getParameter<double>("maxAbsZ")),
      pvMaxRho_(cfg.getParameter<edm::ParameterSet>("goodPv").getParameter<double>("maxRho")),
      minPt_(cfg.getParameter<double>("minPt")),
      minAbsDxyBs_(cfg.getParameter<double>("minAbsDxyBs")),
      maxDxyErr_(cfg.getParameter<double>("maxDxyErr")),
      minNSigmaDxyBs_(cfg.getParameter<double>("minNSigmaDxyBs")),
      minRescaledNSigmaDxyBs_(cfg.getParameter<double>("minRescaledNSigmaDxyBs")),
      minNSigmaDxyPv_(cfg.getParameter<double>("minNSigmaDxyPv")),
      minHits_(cfg.getParameter<int>("minHits")),
      minPixelHits_(cfg.getParameter<int>("minPixelHits")),
      minPixelLayers_(cfg.getParameter<int>("minPixelLayers")),
      minStripLayers_(cfg.getParameter<int>("minStripLayers")),
      maxFirstPixelLayer_(cfg.getParameter<int>("maxFirstPixelLayer")),
      dxyErrScale_(cfg.getParameter<edm::ParameterSet>("dxyErrScale")) {
  produces<reco::TrackCollection>();
  produces<edm::ValueMap<int>>("candIdx");
}

const reco::Vertex* SeedTrackProducer::firstGoodPv(const reco::VertexCollection& pvs) const {
  for (const reco::Vertex& pv : pvs)
    if (!pv.isFake() && pv.ndof() > pvMinNdof_ && std::fabs(pv.z()) <= pvMaxAbsZ_ && pv.position().rho() < pvMaxRho_)
      return &pv;
  return nullptr;
}

bool SeedTrackProducer::isSeed(const reco::Track& tk, const reco::BeamSpot& beamSpot, const reco::Vertex& pv) const {
  const double dxyBs = tk.dxy(beamSpot);
  const double dxyErr = tk.dxyError();
  const reco::HitPattern& hp = tk.hitPattern();

  int firstPixelLayer = 5;
  for (int layer = 1; layer <= 4; ++layer)
    if (hp.hasValidHitInPixelLayer(PixelSubdetector::PixelBarrel, layer)) {
      firstPixelLayer = layer;
      break;
    }

  return tk.pt() > minPt_ && std::fabs(dxyBs) > minAbsDxyBs_ && dxyErr < maxDxyErr_ && std::fabs(dxyBs / dxyErr) > minNSigmaDxyBs_ && std::fabs(dxyBs / dxyErrScale_.rescaledDxyErr(tk)) > minRescaledNSigmaDxyBs_ && std::fabs(tk.dxy(pv.position()) / dxyErr) > minNSigmaDxyPv_ && hp.numberOfValidHits() >= minHits_ && hp.numberOfValidPixelHits() >= minPixelHits_ && hp.pixelLayersWithMeasurement() >= minPixelLayers_ && hp.stripLayersWithMeasurement() >= minStripLayers_ && (firstPixelLayer <= maxFirstPixelLayer_ || (firstPixelLayer == 2 && hp.numberOfLostHits(reco::HitPattern::MISSING_INNER_HITS) == 0));
}

void SeedTrackProducer::produce(edm::StreamID, edm::Event& event, const edm::EventSetup&) const {
  const pat::PackedCandidateCollection& candidates = event.get(candidatesToken_);
  const reco::BeamSpot& beamSpot = event.get(beamSpotToken_);
  const reco::Vertex* pv = firstGoodPv(event.get(primaryVerticesToken_));

  auto seeds = std::make_unique<reco::TrackCollection>();
  std::vector<int> candIdx;

  if (pv)
    for (size_t i = 0, n = candidates.size(); i < n; ++i) {
      const pat::PackedCandidate& cand = candidates[i];
      if (cand.charge() != 0 && cand.hasTrackDetails() && isSeed(cand.pseudoTrack(), beamSpot, *pv)) {
        seeds->push_back(cand.pseudoTrack());
        candIdx.push_back(i);
      }
    }

  const edm::OrphanHandle<reco::TrackCollection> handle = event.put(std::move(seeds));
  auto candIdxMap = std::make_unique<edm::ValueMap<int>>();
  edm::ValueMap<int>::Filler filler(*candIdxMap);
  filler.insert(handle, candIdx.begin(), candIdx.end());
  filler.fill();
  event.put(std::move(candIdxMap), "candIdx");
}

DEFINE_FWK_MODULE(SeedTrackProducer);
