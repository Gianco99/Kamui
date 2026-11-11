# zRefit never checks that the refit is valid, so a failed fit replaces the vertex and later steps drop it.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1419, 1493-1521`. The refit at 1419 goes into the shift test with no `isValid()` check. A failed fit becomes a default `reco::Vertex` at the origin with zero covariance, so its z shift reads as hundreds of sigma and it replaces the vertex (1518). mergeNearby and sharedJets skip the trackless result, and the cleanup at 1937-1940 erases it.
- **Kamui:** `vertexing/plugins/DVProducer.cc:396-403`. Reproduced on purpose to match JMTucker, and the cleanup at 514-515 erases the trackless vertex.
- **Impact:** Minor: every failed refit seen was on a 3-track DV. Skipping them recovers a tight DV in about 2 of 10,000 signal MC events with no region change, and no tight DV in 22,138 data events.
- **Fix:** Check `vnm1.isValid()` right after the refit and move on to the next track when it failed.
