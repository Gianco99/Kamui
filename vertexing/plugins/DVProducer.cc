#include <algorithm>
#include <cmath>
#include <map>
#include <memory>
#include <set>
#include <vector>

#include "DataFormats/BeamSpot/interface/BeamSpot.h"
#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Math/interface/deltaPhi.h"
#include "DataFormats/PatCandidates/interface/Jet.h"
#include "DataFormats/PatCandidates/interface/PackedCandidate.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"
#include "RecoVertex/KalmanVertexFit/interface/KalmanVertexFitter.h"
#include "RecoVertex/VertexTools/interface/VertexDistance3D.h"
#include "RecoVertex/VertexTools/interface/VertexDistanceXY.h"
#include "TrackingTools/IPTools/interface/IPTools.h"
#include "TrackingTools/Records/interface/TransientTrackRecord.h"
#include "TrackingTools/TransientTrack/interface/TransientTrack.h"
#include "TrackingTools/TransientTrack/interface/TransientTrackBuilder.h"

typedef std::set<reco::TrackRef> TrackSet;
typedef std::vector<reco::TrackRef> TrackVec;
typedef std::vector<reco::Vertex>::iterator VertexIter;

class DVProducer : public edm::global::EDProducer<> {
public:
  explicit DVProducer(const edm::ParameterSet&);
  void produce(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

private:
  static constexpr double trackJetMatchScoreBelow = 1.3;

  TrackSet vertexTrackSet(const reco::Vertex&) const;
  TrackVec vertexTrackVec(const reco::Vertex&) const;
  bool isTrackSubset(const TrackSet&, const TrackSet&) const;
  bool fitVertex(KalmanVertexFitter&, std::vector<reco::TransientTrack>&, reco::Vertex&) const;
  int matchedJet(const reco::Track&, const pat::JetCollection&) const;
  std::vector<std::vector<size_t>> loneSharedJetTracks(const std::vector<std::vector<size_t>>&, const std::vector<std::vector<size_t>>&, size_t, size_t) const;

  const edm::EDGetTokenT<reco::TrackCollection> seedTracksToken_;
  const edm::EDGetTokenT<reco::BeamSpot> beamSpotToken_;
  const edm::EDGetTokenT<pat::JetCollection> jetsToken_;
  const edm::ESGetToken<TransientTrackBuilder, TransientTrackRecord> ttBuilderToken_;
  const edm::ParameterSet kalman_;
  const int minTracks_;
  const double maxChi2PerDof_;
  const double sharedTracksMergeBelowSigma_;
  const double sharedTracksKeepBelowSigma_;
  const double sharedTracksTieBelowSigma_;
  const double zRefitMaxShiftSigma_;
  const double mergeNearbyDeltaPhiBelow_;
  const double mergeNearbyDistance2dBelow_;
  const double mergeNearbyDbvAbove_;
  const double sharedJetsMaxDeltaPhi_;

  const VertexDistanceXY vertexDist2d_;
  const VertexDistance3D vertexDist3d_;
};

DVProducer::DVProducer(const edm::ParameterSet& cfg)
    : seedTracksToken_(consumes(cfg.getParameter<edm::InputTag>("seedTracks"))),
      beamSpotToken_(consumes(cfg.getParameter<edm::InputTag>("beamSpot"))),
      jetsToken_(consumes(cfg.getParameter<edm::InputTag>("jets"))),
      ttBuilderToken_(esConsumes(edm::ESInputTag("", "TransientTrackBuilder"))),
      kalman_(cfg.getParameter<edm::ParameterSet>("kalman")),
      minTracks_(cfg.getParameter<int>("minTracks")),
      maxChi2PerDof_(cfg.getParameter<double>("maxChi2PerDof")),
      sharedTracksMergeBelowSigma_(cfg.getParameter<edm::ParameterSet>("sharedTracks").getParameter<double>("mergeBelowSigma")),
      sharedTracksKeepBelowSigma_(cfg.getParameter<edm::ParameterSet>("sharedTracks").getParameter<double>("keepBelowSigma")),
      sharedTracksTieBelowSigma_(cfg.getParameter<edm::ParameterSet>("sharedTracks").getParameter<double>("tieBelowSigma")),
      zRefitMaxShiftSigma_(cfg.getParameter<edm::ParameterSet>("zRefit").getParameter<double>("maxShiftSigma")),
      mergeNearbyDeltaPhiBelow_(cfg.getParameter<edm::ParameterSet>("mergeNearby").getParameter<double>("deltaPhiBelow")),
      mergeNearbyDistance2dBelow_(cfg.getParameter<edm::ParameterSet>("mergeNearby").getParameter<double>("distance2dBelow")),
      mergeNearbyDbvAbove_(cfg.getParameter<edm::ParameterSet>("mergeNearby").getParameter<double>("dbvAbove")),
      sharedJetsMaxDeltaPhi_(cfg.getParameter<edm::ParameterSet>("sharedJets").getParameter<double>("maxDeltaPhi")) {
  produces<reco::VertexCollection>();
  produces<edm::ValueMap<int>>("trackVertexIdx");
}

TrackSet DVProducer::vertexTrackSet(const reco::Vertex& v) const {
  TrackSet result;
  for (auto it = v.tracks_begin(), ite = v.tracks_end(); it != ite; ++it)
    result.insert(it->castTo<reco::TrackRef>());
  return result;
}

TrackVec DVProducer::vertexTrackVec(const reco::Vertex& v) const {
  const TrackSet s = vertexTrackSet(v);
  return TrackVec(s.begin(), s.end());
}

bool DVProducer::isTrackSubset(const TrackSet& a, const TrackSet& b) const {
  const TrackSet& smaller = a.size() <= b.size() ? a : b;
  const TrackSet& bigger = a.size() <= b.size() ? b : a;
  for (auto tk : smaller)
    if (bigger.count(tk) < 1)
      return false;
  return true;
}

bool DVProducer::fitVertex(KalmanVertexFitter& fitter, std::vector<reco::TransientTrack>& ttks, reco::Vertex& out) const {
  if (ttks.size() < 2)
    return false;
  const TransientVertex tv = fitter.vertex(ttks);
  if (tv.normalisedChiSquared() > maxChi2PerDof_)
    return false;
  out = reco::Vertex(tv);
  return true;
}

int DVProducer::matchedJet(const reco::Track& tk, const pat::JetCollection& jets) const {
  double best = trackJetMatchScoreBelow;
  int jetIndex = -1;
  for (size_t j = 0; j < jets.size(); ++j)
    for (size_t idau = 0, idaue = jets[j].numberOfDaughters(); idau < idaue; ++idau) {
      const reco::Candidate* dau = jets[j].daughter(idau);
      if (dau->charge() == 0)
        continue;
      const pat::PackedCandidate* packed = dynamic_cast<const pat::PackedCandidate*>(dau);
      if (!packed || packed->charge() == 0 || !packed->hasTrackDetails())
        continue;
      const reco::Track& jtk = packed->pseudoTrack();
      const double match = (std::fabs(tk.pt() - std::fabs(jtk.charge() * jtk.pt())) + 1) * (std::fabs(tk.eta() - jtk.eta()) + 1) * (std::fabs(tk.phi() - jtk.phi()) + 1);
      if (match < best) {
        best = match;
        jetIndex = j;
      }
    }
  return jetIndex;
}

std::vector<std::vector<size_t>> DVProducer::loneSharedJetTracks(const std::vector<std::vector<size_t>>& jetIdx, const std::vector<std::vector<size_t>>& trackIdx, size_t iv0, size_t iv1) const {
  std::vector<std::vector<size_t>> lone(2);
  std::vector<size_t> shared;
  for (size_t jet : jetIdx[iv0])
    if (std::find(jetIdx[iv1].begin(), jetIdx[iv1].end(), jet) != jetIdx[iv1].end() && std::find(shared.begin(), shared.end(), jet) == shared.end())
      shared.push_back(jet);

  for (size_t jet : shared)
    for (int i = 0; i < 2; ++i) {
      const size_t iv = i == 0 ? iv0 : iv1;
      std::vector<size_t> tracks;
      for (size_t k = 0; k < jetIdx[iv].size(); ++k)
        if (jetIdx[iv][k] == jet)
          tracks.push_back(trackIdx[iv][k]);
      if (tracks.size() == 1)
        lone[i].push_back(tracks[0]);
    }
  return lone;
}

void DVProducer::produce(edm::StreamID, edm::Event& event, const edm::EventSetup& setup) const {
  const reco::BeamSpot& beamSpot = event.get(beamSpotToken_);
  const double bsx = beamSpot.position().x();
  const double bsy = beamSpot.position().y();
  const reco::Vertex beamSpotVertex(beamSpot.position(), beamSpot.covariance3D());
  const TransientTrackBuilder& ttBuilder = setup.getData(ttBuilderToken_);

  const edm::Handle<reco::TrackCollection> seedTracks = event.getHandle(seedTracksToken_);
  KalmanVertexFitter fitter(kalman_, kalman_.getParameter<bool>("doSmoothing"));

  std::vector<reco::TransientTrack> transientTracks;
  std::map<reco::TrackRef, size_t> trackIndex;
  for (size_t i = 0, ie = seedTracks->size(); i < ie; ++i) {
    const reco::TrackRef tk(seedTracks, i);
    transientTracks.push_back(ttBuilder.build(tk));
    trackIndex[tk] = i;
  }

  auto vertices = std::make_unique<reco::VertexCollection>();

  for (size_t i = 0, ie = transientTracks.size(); i < ie; ++i)
    for (size_t j = i + 1; j < ie; ++j) {
      std::vector<reco::TransientTrack> ttks{transientTracks[i], transientTracks[j]};
      const TransientVertex seed = fitter.vertex(ttks);
      if (seed.isValid() && seed.normalisedChiSquared() < maxChi2PerDof_)
        vertices->push_back(reco::Vertex(seed));
    }

  VertexIter v[2];
  for (v[0] = vertices->begin(); v[0] != vertices->end(); ++v[0]) {
    TrackSet tracks[2];
    tracks[0] = vertexTrackSet(*v[0]);
    if (tracks[0].size() < 2) {
      v[0] = vertices->erase(v[0]) - 1;
      continue;
    }

    bool duplicate = false, merge = false, refit = false;
    TrackSet toRemove[2];

    for (v[1] = v[0] + 1; v[1] != vertices->end(); ++v[1]) {
      tracks[1] = vertexTrackSet(*v[1]);
      if (tracks[1].size() < 2) {
        v[1] = vertices->erase(v[1]) - 1;
        continue;
      }

      if (isTrackSubset(tracks[0], tracks[1])) {
        duplicate = true;
        break;
      }

      TrackVec shared;
      for (auto tk : tracks[0])
        if (tracks[1].count(tk) > 0)
          shared.push_back(tk);
      if (shared.empty())
        continue;

      const Measurement1D vertexDist = vertexDist3d_.distance(*v[0], *v[1]);
      if (vertexDist.significance() < sharedTracksMergeBelowSigma_)
        merge = true;
      else
        refit = true;

      const reco::TransientTrack& ttk = transientTracks[trackIndex.at(shared[0])];
      std::pair<bool, Measurement1D> dist0 = IPTools::absoluteImpactParameter3D(ttk, *v[0]);
      std::pair<bool, Measurement1D> dist1 = IPTools::absoluteImpactParameter3D(ttk, *v[1]);
      dist0.first = dist0.first && dist0.second.significance() < sharedTracksKeepBelowSigma_;
      dist1.first = dist1.first && dist1.second.significance() < sharedTracksKeepBelowSigma_;
      bool removeFrom0 = !dist0.first;
      bool removeFrom1 = !dist1.first;
      if (dist0.second.significance() < sharedTracksTieBelowSigma_ && dist1.second.significance() < sharedTracksTieBelowSigma_) {
        if (tracks[0].size() > tracks[1].size())
          removeFrom1 = true;
        else
          removeFrom0 = true;
      } else if (dist0.second.significance() < dist1.second.significance())
        removeFrom1 = true;
      else
        removeFrom0 = true;

      if (removeFrom0)
        toRemove[0].insert(shared[0]);
      if (removeFrom1)
        toRemove[1].insert(shared[0]);

      break;
    }

    if (duplicate) {
      vertices->erase(v[1]);
    } else if (merge) {
      TrackSet toFit;
      for (int i = 0; i < 2; ++i)
        for (auto tk : tracks[i])
          toFit.insert(tk);

      std::vector<reco::TransientTrack> ttks;
      for (auto tk : toFit)
        ttks.push_back(transientTracks[trackIndex.at(tk)]);

      reco::Vertex merged;
      if (fitVertex(fitter, ttks, merged) && vertexTrackSet(merged) == toFit) {
        vertices->erase(v[1]);
        *v[0] = merged;
      } else
        refit = true;
    }

    if (refit) {
      bool erase[2] = {false, false};
      for (int i = 0; i < 2; ++i) {
        if (toRemove[i].empty())
          continue;

        std::vector<reco::TransientTrack> ttks;
        for (auto tk : tracks[i])
          if (toRemove[i].count(tk) == 0)
            ttks.push_back(transientTracks[trackIndex.at(tk)]);

        reco::Vertex refitted;
        if (fitVertex(fitter, ttks, refitted))
          *v[i] = refitted;
        else
          erase[i] = true;
      }

      if (erase[1])
        vertices->erase(v[1]);
      if (erase[0])
        vertices->erase(v[0]);
    }

    if (duplicate || merge || refit)
      v[0] = vertices->begin() - 1;
  }

  for (v[0] = vertices->begin(); v[0] != vertices->end(); ++v[0]) {
    const TrackVec tks = vertexTrackVec(*v[0]);
    const size_t ntks = tks.size();
    if (ntks < 3)
      continue;

    std::vector<reco::TransientTrack> ttks(ntks - 1);
    for (size_t i = 0; i < ntks; ++i) {
      for (size_t j = 0; j < ntks; ++j)
        if (j != i)
          ttks[j - (j >= i)] = ttBuilder.build(tks[j]);

      const reco::Vertex vnm1(TransientVertex(fitter.vertex(ttks)));
      const double distz = vnm1.z() - v[0]->z();
      const double distzSig = distz / std::sqrt(std::fabs(vnm1.covariance(2, 2) - v[0]->covariance(2, 2)));

      if (vnm1.chi2() < 0 || std::fabs(distzSig) > zRefitMaxShiftSigma_) {
        *v[0] = vnm1;
        --v[0];
        break;
      }
    }
  }

  for (v[0] = vertices->begin(); v[0] != vertices->end(); ++v[0])
    if (v[0]->normalizedChi2() > maxChi2PerDof_)
      v[0] = vertices->erase(v[0]) - 1;

  for (v[0] = vertices->begin(); v[0] != vertices->end(); ++v[0]) {
    TrackSet tracks[2];
    tracks[0] = vertexTrackSet(*v[0]);

    bool merged = false;
    for (v[1] = v[0] + 1; v[1] != vertices->end(); ++v[1]) {
      if (vertices->size() < 2 || v[0]->nTracks() < 2 || v[1]->nTracks() < 2)
        continue;

      tracks[1] = vertexTrackSet(*v[1]);
      const double dist2d = vertexDist2d_.distance(*v[0], *v[1]).value();
      const double dbv0 = vertexDist2d_.distance(*v[0], beamSpotVertex).value();
      const double dbv1 = vertexDist2d_.distance(*v[1], beamSpotVertex).value();
      const double phi0 = atan2(v[0]->y() - bsy, v[0]->x() - bsx);
      const double phi1 = atan2(v[1]->y() - bsy, v[1]->x() - bsx);
      if (std::fabs(reco::deltaPhi(phi0, phi1)) >= mergeNearbyDeltaPhiBelow_ || dist2d >= mergeNearbyDistance2dBelow_ || dbv0 <= mergeNearbyDbvAbove_ || dbv1 <= mergeNearbyDbvAbove_)
        continue;

      TrackSet toFit;
      for (int i = 0; i < 2; ++i)
        for (auto tk : tracks[i])
          toFit.insert(tk);

      std::vector<reco::TransientTrack> ttks;
      for (auto tk : toFit)
        ttks.push_back(transientTracks[trackIndex.at(tk)]);

      reco::Vertex mergedVertex;
      if (fitVertex(fitter, ttks, mergedVertex) && vertexTrackSet(mergedVertex) == toFit) {
        merged = true;
        v[1] = vertices->erase(v[1]) - 1;
        *v[0] = mergedVertex;
      }
    }

    if (merged)
      v[0] = vertices->begin() - 1;
  }

  const pat::JetCollection& jets = event.get(jetsToken_);
  std::vector<TrackVec> vertexTracks;
  std::vector<std::vector<size_t>> keptTrackIdx, matchedTrackIdx, matchedJetIdx;
  std::vector<size_t> byNtracks;

  for (v[0] = vertices->begin(); v[0] != vertices->end(); ++v[0]) {
    const TrackVec tks = vertexTrackVec(*v[0]);
    std::vector<size_t> kept, matchedTracks, matchedJets;
    for (size_t i = 0; i < tks.size(); ++i) {
      kept.push_back(i);
      const int jet = matchedJet(*tks[i], jets);
      if (jet >= 0) {
        matchedTracks.push_back(i);
        matchedJets.push_back(size_t(jet));
      }
    }
    vertexTracks.push_back(tks);
    keptTrackIdx.push_back(kept);
    matchedTrackIdx.push_back(matchedTracks);
    matchedJetIdx.push_back(matchedJets);
    byNtracks.push_back(vertexTracks.size() - 1);
  }

  std::stable_sort(byNtracks.begin(), byNtracks.end(), [&](size_t a, size_t b) {
    if (vertexTracks[a].size() != vertexTracks[b].size())
      return vertexTracks[a].size() < vertexTracks[b].size();
    return a > b;
  });

  for (size_t i = 0; i < byNtracks.size(); ++i) {
    const double phi0 = atan2(vertices->at(byNtracks[i]).y() - bsy, vertices->at(byNtracks[i]).x() - bsx);
    for (size_t j = 0; j < byNtracks.size(); ++j) {
      if (i == j)
        continue;
      const size_t iv0 = byNtracks[i], iv1 = byNtracks[j];
      reco::Vertex& sv0 = vertices->at(iv0);
      if (sv0.nTracks() <= 2 || vertices->at(iv1).nTracks() <= 2)
        continue;

      const std::vector<std::vector<size_t>> lone = loneSharedJetTracks(matchedJetIdx, matchedTrackIdx, iv0, iv1);
      if (lone[0].empty() && lone[1].empty())
        continue;

      for (size_t idx : lone[0])
        if (std::fabs(reco::deltaPhi(vertexTracks[iv0][idx]->phi(), phi0)) > sharedJetsMaxDeltaPhi_)
          keptTrackIdx[iv0].erase(std::remove(keptTrackIdx[iv0].begin(), keptTrackIdx[iv0].end(), idx), keptTrackIdx[iv0].end());

      TrackSet kept;
      for (size_t idx : keptTrackIdx[iv0])
        kept.insert(vertexTracks[iv0][idx]);

      std::vector<reco::TransientTrack> ttks;
      for (auto tk : kept)
        ttks.push_back(ttBuilder.build(tk));

      reco::Vertex resolved;
      fitVertex(fitter, ttks, resolved);
      sv0 = resolved;
    }
  }

  for (v[0] = vertices->begin(); v[0] != vertices->end(); ++v[0]) {
    const TrackSet tracks = vertexTrackSet(*v[0]);
    if (tracks.size() < 2) {
      v[0] = vertices->erase(v[0]) - 1;
      continue;
    }
    if (tracks.size() < v[0]->nTracks())
      throw cms::Exception("DVProducer") << "Vertex holds duplicated tracks";
  }

  std::vector<int> trackVertexIdx(seedTracks->size(), -1);
  auto kept = std::make_unique<reco::VertexCollection>();
  for (const reco::Vertex& vtx : *vertices) {
    const TrackSet tracks = vertexTrackSet(vtx);
    if (int(tracks.size()) < minTracks_)
      continue;
    for (auto tk : tracks)
      trackVertexIdx[trackIndex.at(tk)] = kept->size();
    kept->push_back(vtx);
  }

  event.put(std::move(kept));
  auto idxMap = std::make_unique<edm::ValueMap<int>>();
  edm::ValueMap<int>::Filler filler(*idxMap);
  filler.insert(seedTracks, trackVertexIdx.begin(), trackVertexIdx.end());
  filler.fill();
  event.put(std::move(idxMap), "trackVertexIdx");
}

DEFINE_FWK_MODULE(DVProducer);
