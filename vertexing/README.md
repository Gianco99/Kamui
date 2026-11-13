# Vertexing

This folder reconstructs DVs: vertices fit from displaced tracks, the tracks that pass far from the beamspot. Its CMSSW plugins run inside the ntuple production job when the content preset includes the vertexing collections, as the Run 2 `dvFull` and every preset built on it do.

In short, the vertexer picks seed tracks, fits pairs of them into seed vertices, cleans those vertices up in a few steps, and writes the ones with enough tracks as the `DV` collection. The two plugins split that work:

- `plugins/SeedTrackProducer.cc` selects the seed tracks the vertices are built from.
- `plugins/DVProducer.cc` fits the vertices.

## Seed Tracks

A seed track is a charged `packedPFCandidates` entry that carries full track information and passes the `seeding` cuts of the `SeedTrack` collection in `config/content/*/collections/vertexing.json`.

- Events without a good PV get no seed tracks.
- In MC, `trackDrop` drops each candidate track at random before the seed cuts, with a probability that grows with its distance to the beamspot.
- `SeedTrack_candIdx` is each track's index in `packedPFCandidates`.
- In MC, `trackErrScale` corrects each track's uncertainties before the significance cut, `nSigmaDxyBsAbove`. A corrected copy of every seed track is kept for the `DV_dBVErr` refit, and the `SeedTrack` branches hold the uncorrected tracks.

## Vertices

Every pair of seed tracks is fit, and each pair passing `maxChi2PerDof` becomes a seed vertex. The steps below then run in order. Each step reads its keys from a block of the same name under the `vertexing` key of the `DV` collection, in the same `vertexing.json`:

```
"sharedTracks": {"mergeBelowSigma": <n>, "keepBelowSigma": <n>, "tieBelowSigma": <n>}
```

1. `sharedTracks` handles a track shared by two vertices.
   - The two vertices merge when they are closer than `mergeBelowSigma`.
   - Otherwise the track stays with the vertex it is closer to, or, when it is closer than `tieBelowSigma` to both, with the vertex holding more tracks.
   - The track stays in a vertex only if it is closer than `keepBelowSigma` to it.
2. `zRefit` drops each track in turn and refits the vertex.
   - It skips a vertex with fewer than a minimum number of tracks, hard-coded in `plugins/DVProducer.cc`.
   - The refit replaces the vertex when it moves the vertex in z by more than `maxShiftSigma` sigma, or when its chi2 is negative.
   - After `zRefit`, every vertex whose chi2 per degree of freedom is above `maxChi2PerDof` is dropped.
3. `mergeNearby` merges two vertices when both of these hold:
   - They are closer than `deltaPhiBelow` in phi and `distance2dBelow` in 2D.
   - Each is farther than `dbvAbove` from the beamspot.
4. `sharedJets` drops a lone shared-jet track, a vertex's only track in a jet it shares with another vertex, when it points more than `maxDeltaPhi` away from its vertex in phi.
   - The jets are the `VertexJet` collection.

What the vertexer writes:

- The `DV` collection keeps the vertices with at least `minTracks` tracks.
- `SeedTrack_dvIdx` is the DV each seed track ended up in, or -1 for a track in none.
- Every kept DV also gets the quantities the analysis selection cuts on:
  - `DV_dBV`: its 2D distance from the beamspot, taken at the DV's z.
  - `DV_dBVErr`: the uncertainty on `DV_dBV`, from refitting the DV with the corrected seed-track copies. In data the copies are the tracks themselves.
  - `DV_mass` and `DV_sumPt`: the invariant mass of its tracks, taken as pions, and their scalar pT sum.
  - `DV_insideBeampipe`: whether it lies inside the `beampipe` circle.
- The `DVTrack` table copies out the uncorrected seed tracks of every kept DV, one row per track, so a revertexer can rebuild the DVs from the ntuple.
  - `DVTrack_dvIdx` is the DV each row belongs to, and a DV's rows come in the order its fit took them.
  - Each row holds the track's charge, chi2, ndof, reference point, momentum and 5x5 covariance. Refitting a DV's rows the way the vertexer does gives back its stored position.
- Vertices outside the beampipe are kept here, since that cut belongs to the selection stage.

## Constants

These cuts are hard-coded in `plugins/DVProducer.cc`:

- A track matches a jet when (1 + |dpT|)(1 + |deta|)(1 + |dphi|) against one of the jet's tracks is below `trackJetMatchScoreBelow`.
- `sharedJets` only compares vertices that each hold a minimum number of tracks.

## Known JMTucker Bugs

Kamui reproduces the bugs found in JMTucker's vertexing that change its output, so the two match exactly until the framework is fully validated. Each bug has a file in `Bugs/jmtucker/adapted/` that says where it lives in both frameworks and how to fix it.

## Caveats

- `DV_dBVErr` copies two odd values from JMTucker, each with its file in `Bugs/jmtucker/adapted/`. It is 0 when the refit fails, which passes any upper cut, and NaN when JMTucker would drop the DV for a NaN uncertainty, which fails any cut on it.
- The Kalman fit is order sensitive. Every fit takes its tracks in seed-track order, so changing that order changes the vertices.
