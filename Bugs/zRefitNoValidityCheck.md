# zRefit never checks that the refit is valid, so a failed fit replaces the vertex and the next steps drop it.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1419, 1493-1521`. The refit at 1419 goes straight into the shift test with no `isValid()` check, and a failed fit converts to a default `reco::Vertex` at the origin with zero covariance, so its z shift reads as hundreds of sigma and it replaces the vertex at 1518. The trackless result is skipped by mergeNearby and sharedJets and erased by the cleanup at 1937-1940.
- **Kamui:** `vertexing/plugins/DVProducer.cc:369-376`. Reproduced on purpose to match JMTucker, and the trackless vertex is erased at 487-488.
- **Fix:** Check `vnm1.isValid()` right after the refit and move on to the next track when it failed.
