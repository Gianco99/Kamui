# Vertexing

DV reconstruction. It runs inside the ntuple production job as CMSSW plugins, switched on by a content collection.

`plugins/SeedTrackProducer.cc` - Selects the seed tracks the vertexer is built from.
## Seed Tracks

A seed track is a charged `packedPFCandidates` entry with track details that passes the `seeding` cuts of the `SeedTrack` collection in `config/content/<era>/collections/vertexing.json`.

- Events without a good primary vertex get no seed tracks.
- `SeedTrack_candIdx` is each track's index in `packedPFCandidates`.
- NOTE: Track dropping is planned but not yet included.

See `config/content/README.md` for the `seeding` fields.
