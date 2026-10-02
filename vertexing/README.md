# Vertexing

This folder reconstructs DVs: vertices fit from displaced tracks, the tracks that pass far from the beamspot. Its CMSSW plugins run inside the ntuple production job when the content preset includes the vertexing collections.

`plugins/SeedTrackProducer.cc`: Selects the seed tracks the vertices are built from.

`plugins/DVProducer.cc`: Fits the vertices.
## Seed Tracks

A seed track is a charged `packedPFCandidates` entry that carries full track information and passes the `seeding` cuts of the `SeedTrack` collection in `config/content/*/collections/vertexing.json`.

- Events without a good PV get no seed tracks.
- In MC, `trackDrop` drops each candidate track at random before the seed cuts, with a probability growing with its distance to the beamspot.
- `SeedTrack_candIdx` is each track's index in `packedPFCandidates`.

## Vertices

Every pair of seed tracks is fit, and pairs passing `maxChi2PerDof` become seed vertices. Then, in order:

1. `sharedTracks`: handles a track shared by two vertices.
   - The two vertices merge when they are closer than `mergeBelowSigma`.
   - Otherwise the track stays with the vertex it is closer to, or with the one holding more tracks when it is closer than `tieBelowSigma` to both.
   - The track leaves any vertex it is not closer than `keepBelowSigma` to.
2. `zRefit`: each track is dropped in turn and the vertex refit.
   - The refit replaces the vertex when it moves the vertex in z by more than `maxShiftSigma` sigma.
3. `mergeNearby`: two vertices are merged when both hold:
   - They are closer than `deltaPhiBelow` in phi and `distance2dBelow` in 2D.
   - Each is farther than `dbvAbove` from the beamspot.
4. `sharedJets`: a lone shared-jet track pointing more than `maxDeltaPhi` away from its vertex is dropped.
   - The jets are the `VertexJet` collection.

Output:

- The `DV` collection keeps the vertices with at least `minTracks` tracks.
- `SeedTrack_dvIdx` is the vertex each seed track ended up in, and -1 for tracks in none. 
- Vertices outside the beampipe are kept here, since that cut belongs to the selection stage. 

## Constants

Cuts hard-coded in `plugins/DVProducer.cc`:
- A track matches a jet when (1 + |dpT|)(1 + |deta|)(1 + |dphi|) against one of the jet's tracks is below `trackJetMatchScoreBelow`.
- `sharedJets` only compares vertices that each hold a minimum number of tracks.

## Known JMTucker Bugs

When porting the vertexing code from JMTucker, bugs were identified. For the sake of consistency with the original framework, these bugs are also ported and will be addressed after full validation of the framework is completed.

- A negative fit chi2 passes every chi2 cut, so a fit that failed badly is accepted.
- Seeding keeps a fit strictly below `maxChi2PerDof`, while every later fit passes at or below it.
- `zRefit` treats a negative refit chi2 as a reason to drop the track.
- `zRefit` never checks that the refit is valid. A failed fit comes back at the origin, reads as a shift of hundreds of sigma, and replaces the vertex, which the next steps then drop.
- The `zRefit` significance divides the z shift by the square root of the difference of two nearly equal z variances, so a tiny numerical difference in the fits can move it across `maxShiftSigma`.
- Track-jet matching compares phi without wrapping.
- A shared-jet refit that fails leaves an empty vertex, which the next sweep drops.
- `sharedJets` tests all of a vertex's lone tracks against the vertex's phi from before its first refit in this step, so later refits never update that phi.
- `mergeNearby` keeps the first vertex's original track list after a merge, so a second merge in the same sweep fits the stale set.

## Caveats

- The MC track drop draws from an engine seeded by each event's run, lumi and event number, so an event always drops the same tracks, no matter the job configuration.
  - Because every event has its own seed, the drops in different jobs are independent.
  - JMTucker seeds its engine once per job and keeps drawing from it event after event, so its drops cannot be replayed.
- Seed tracks keep their `packedPFCandidates` order. Every fit takes its tracks in that order too, since `plugins/DVProducer.cc` gathers them in a `std::set<reco::TrackRef>`, which sorts them by seed-track index. The Kalman fit is order sensitive!
- `DxyErrScale` scales only the dxy diagonal of the covariance.
- A plugin name must be unique across all of CMSSW, the release included. Before naming a new one, grep `$CMSSW_RELEASE_BASE/lib/$SCRAM_ARCH/.edmplugincache` for it.
