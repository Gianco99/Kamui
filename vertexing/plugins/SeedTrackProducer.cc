#include <algorithm>
#include <cmath>
#include <random>
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

class ErrScaleCurve {
public:
  explicit ErrScaleCurve(const edm::ParameterSet&);
  double at(double pt) const;

private:
  enum class Form { none, constant, subtractScaledExp, subtractShiftedExp, subtractScaledExpPlusLinear };

  static Form parseForm(const std::string&);

  const Form form_;
  const std::vector<double> p_;
};

ErrScaleCurve::Form ErrScaleCurve::parseForm(const std::string& form) {
  if (form == "none")
    return Form::none;
  if (form == "p0")
    return Form::constant;
  if (form == "p0-p2*exp(-p1*x)")
    return Form::subtractScaledExp;
  if (form == "p0-exp(-p1*x+p2)")
    return Form::subtractShiftedExp;
  if (form == "p0-p2*exp(-p1*x)+p3*x")
    return Form::subtractScaledExpPlusLinear;
  throw cms::Exception("SeedTrackProducer") << "Unknown trackErrScale form '" << form << "'";
}

ErrScaleCurve::ErrScaleCurve(const edm::ParameterSet& cfg) : form_(parseForm(cfg.getParameter<std::string>("form"))), p_(cfg.getParameter<std::vector<double>>("p")) {
  const size_t nParams = form_ == Form::none ? 0 : form_ == Form::constant ? 1 : form_ == Form::subtractScaledExpPlusLinear ? 4 : 3;
  if (p_.size() != nParams)
    throw cms::Exception("SeedTrackProducer") << "trackErrScale form '" << cfg.getParameter<std::string>("form") << "' needs " << nParams << " parameters";
}

double ErrScaleCurve::at(double x) const {
  switch (form_) {
    case Form::none:
      return 1;
    case Form::constant:
      return p_[0];
    case Form::subtractScaledExp:
      return p_[0] - p_[2] * exp(-p_[1] * x);
    case Form::subtractShiftedExp:
      return p_[0] - exp(-p_[1] * x + p_[2]);
    case Form::subtractScaledExpPlusLinear:
      return p_[0] - p_[2] * exp(-p_[1] * x) + p_[3] * x;
  }
  return 1;
}

// Scales a track's dxy and dsz uncertainties by curves in its pT, separately in the barrel and the endcap
class TrackErrScale {
public:
  explicit TrackErrScale(const edm::ParameterSet&);
  reco::Track rescaled(const reco::Track&) const;

private:
  struct Region {
    explicit Region(const edm::ParameterSet& cfg) : dxy(cfg.getParameter<edm::ParameterSet>("dxy")), dsz(cfg.getParameter<edm::ParameterSet>("dsz")), dxyDsz(cfg.getParameter<edm::ParameterSet>("dxyDsz")) {}
    const ErrScaleCurve dxy, dsz, dxyDsz;
  };

  const double barrelAbsEtaBelow_;
  const Region barrel_;
  const Region endcap_;
};

TrackErrScale::TrackErrScale(const edm::ParameterSet& cfg)
    : barrelAbsEtaBelow_(cfg.getParameter<double>("barrelAbsEtaBelow")), barrel_(cfg.getParameter<edm::ParameterSet>("barrel")), endcap_(cfg.getParameter<edm::ParameterSet>("endcap")) {}

reco::Track TrackErrScale::rescaled(const reco::Track& tk) const {
  const Region& region = std::fabs(tk.eta()) < barrelAbsEtaBelow_ ? barrel_ : endcap_;
  const double dxy = region.dxy.at(tk.pt());
  const double dsz = region.dsz.at(tk.pt());
  const int iDxy = reco::TrackBase::i_dxy;
  const int iDsz = reco::TrackBase::i_dsz;

  // The dxy and dsz rows of the symmetric covariance scale by the curve, their diagonal entries by its square, and the dxy-dsz entry also by the correlation curve
  reco::TrackBase::CovarianceMatrix cov = tk.covariance();
  for (int i = 0; i < reco::TrackBase::dimension; ++i)
    cov(i, iDxy) *= i == iDxy ? pow(dxy, 2) : dxy;
  for (int i = 0; i < reco::TrackBase::dimension; ++i)
    cov(i, iDsz) *= i == iDsz ? pow(dsz, 2) : dsz;
  cov(iDxy, iDsz) *= region.dxyDsz.at(tk.pt());
  return reco::Track(tk.chi2(), tk.ndof(), tk.referencePoint(), tk.momentum(), tk.charge(), cov, tk.algo());
}

class SeedTrackProducer : public edm::global::EDProducer<> {
public:
  explicit SeedTrackProducer(const edm::ParameterSet&);
  void produce(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

private:
  const reco::Vertex* firstGoodPv(const reco::VertexCollection&) const;
  bool isSeed(const reco::Track&, double dxyErr, const reco::BeamSpot&) const;
  bool isDropped(const reco::Track&, const reco::BeamSpot&, std::mt19937_64&) const;

  const edm::EDGetTokenT<pat::PackedCandidateCollection> candidatesToken_;
  const edm::EDGetTokenT<reco::BeamSpot> beamSpotToken_;
  const edm::EDGetTokenT<reco::VertexCollection> primaryVerticesToken_;
  const double pvNdofAbove_;
  const double pvMaxAbsZ_;
  const double pvRhoBelow_;
  const double ptAbove_;
  const double nSigmaDxyBsAbove_;
  const int minPixelLayers_;
  const int minStripLayers_;
  const int maxFirstPixelLayer_;
  const TrackErrScale trackErrScale_;
  const double trackDropCoefficient_;
  const double trackDropAbsDxyBsCap_;
};

SeedTrackProducer::SeedTrackProducer(const edm::ParameterSet& cfg)
    : candidatesToken_(consumes(cfg.getParameter<edm::InputTag>("src"))),
      beamSpotToken_(consumes(cfg.getParameter<edm::InputTag>("beamSpot"))),
      primaryVerticesToken_(consumes(cfg.getParameter<edm::InputTag>("primaryVertices"))),
      pvNdofAbove_(cfg.getParameter<edm::ParameterSet>("goodPv").getParameter<double>("ndofAbove")),
      pvMaxAbsZ_(cfg.getParameter<edm::ParameterSet>("goodPv").getParameter<double>("maxAbsZ")),
      pvRhoBelow_(cfg.getParameter<edm::ParameterSet>("goodPv").getParameter<double>("rhoBelow")),
      ptAbove_(cfg.getParameter<double>("ptAbove")),
      nSigmaDxyBsAbove_(cfg.getParameter<double>("nSigmaDxyBsAbove")),
      minPixelLayers_(cfg.getParameter<int>("minPixelLayers")),
      minStripLayers_(cfg.getParameter<int>("minStripLayers")),
      maxFirstPixelLayer_(cfg.getParameter<int>("maxFirstPixelLayer")),
      trackErrScale_(cfg.getParameter<edm::ParameterSet>("trackErrScale")),
      trackDropCoefficient_(cfg.getParameter<edm::ParameterSet>("trackDrop").getParameter<double>("coefficient")),
      trackDropAbsDxyBsCap_(cfg.getParameter<edm::ParameterSet>("trackDrop").getParameter<double>("absDxyBsCap")) {
  produces<reco::TrackCollection>();
  produces<reco::TrackCollection>("rescaled");
  produces<edm::ValueMap<int>>("candIdx");
  produces<reco::VertexCollection>("goodPv");
}

const reco::Vertex* SeedTrackProducer::firstGoodPv(const reco::VertexCollection& pvs) const {
  for (const reco::Vertex& pv : pvs)
    if (!pv.isFake() && pv.ndof() > pvNdofAbove_ && std::fabs(pv.z()) <= pvMaxAbsZ_ && pv.position().rho() < pvRhoBelow_)
      return &pv;
  return nullptr;
}

bool SeedTrackProducer::isSeed(const reco::Track& tk, double dxyErr, const reco::BeamSpot& beamSpot) const {
  const reco::HitPattern& hp = tk.hitPattern();

  int firstPixelLayer = 5;
  for (int layer = 1; layer <= 4; ++layer)
    if (hp.hasValidHitInPixelLayer(PixelSubdetector::PixelBarrel, layer)) {
      firstPixelLayer = layer;
      break;
    }

  return tk.pt() > ptAbove_ && std::fabs(tk.dxy(beamSpot) / dxyErr) > nSigmaDxyBsAbove_ && hp.pixelLayersWithMeasurement() >= minPixelLayers_ && hp.stripLayersWithMeasurement() >= minStripLayers_ && (firstPixelLayer <= maxFirstPixelLayer_ || (firstPixelLayer == 2 && hp.numberOfLostHits(reco::HitPattern::MISSING_INNER_HITS) == 0));
}

bool SeedTrackProducer::isDropped(const reco::Track& tk, const reco::BeamSpot& beamSpot, std::mt19937_64& engine) const {
  const double absDxyBs = std::min(std::fabs(tk.dxy(beamSpot)), trackDropAbsDxyBsCap_);
  return std::generate_canonical<double, 53>(engine) > 1 - trackDropCoefficient_ * absDxyBs * absDxyBs;
}

void SeedTrackProducer::produce(edm::StreamID, edm::Event& event, const edm::EventSetup&) const {
  const pat::PackedCandidateCollection& candidates = event.get(candidatesToken_);
  const reco::BeamSpot& beamSpot = event.get(beamSpotToken_);
  const reco::Vertex* pv = firstGoodPv(event.get(primaryVerticesToken_));
  std::seed_seq seed{event.id().run(), event.id().luminosityBlock(), unsigned(event.id().event()), unsigned(event.id().event() >> 32)};
  std::mt19937_64 engine(seed);

  auto seeds = std::make_unique<reco::TrackCollection>();
  auto rescaledSeeds = std::make_unique<reco::TrackCollection>();
  std::vector<int> candIdx;

  if (pv)
    for (size_t i = 0, n = candidates.size(); i < n; ++i) {
      const pat::PackedCandidate& cand = candidates[i];
      if (cand.charge() == 0 || !cand.hasTrackDetails() || (trackDropCoefficient_ > 0 && isDropped(cand.pseudoTrack(), beamSpot, engine)))
        continue;
      const reco::Track rescaled = trackErrScale_.rescaled(cand.pseudoTrack());
      if (isSeed(cand.pseudoTrack(), rescaled.dxyError(), beamSpot)) {
        seeds->push_back(cand.pseudoTrack());
        rescaledSeeds->push_back(rescaled);
        candIdx.push_back(i);
      }
    }

  const edm::OrphanHandle<reco::TrackCollection> handle = event.put(std::move(seeds));
  event.put(std::move(rescaledSeeds), "rescaled");
  auto candIdxMap = std::make_unique<edm::ValueMap<int>>();
  edm::ValueMap<int>::Filler filler(*candIdxMap);
  filler.insert(handle, candIdx.begin(), candIdx.end());
  filler.fill();
  event.put(std::move(candIdxMap), "candIdx");
  // The PV the seeds were chosen with (none when the event has no good PV), for DVProducer
  auto goodPv = std::make_unique<reco::VertexCollection>();
  if (pv)
    goodPv->push_back(*pv);
  event.put(std::move(goodPv), "goodPv");
}

DEFINE_FWK_MODULE(SeedTrackProducer);
