# zRefit drops a track whenever the refit without it returns a negative chi2.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1493, 1518-1521`. `vnm1.chi2() < 0` is a replace condition, so a refit without track i that returns a negative chi2 replaces the vertex and the track is gone. The chi2/dof filter after zRefit (1528) keeps the result, since a negative chi2/dof is never `> 5`.
- **Kamui:** `vertexing/plugins/DVProducer.cc:400-403`. Reproduced on purpose to match JMTucker.
- **Impact:** Minor: it happened 6 times in 39.8k events, always in a vertex outside the beampipe, so no tight DV changed.
- **Fix:** Treat a negative refit chi2 as a failed refit: move on to the next track and keep the current vertex.
