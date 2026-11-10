# zRefit treats a negative refit chi2 as a reason to drop the track.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1493, 1518-1521`. `vnm1.chi2() < 0` is one of the replace conditions, so a refit without track i that comes back with a negative chi2 replaces the vertex and that track is gone. The chi2/dof filter after zRefit (1528) keeps the result, since a negative chi2/dof passes `> 5`.
- **Kamui:** `vertexing/plugins/DVProducer.cc:379-382`. Reproduced on purpose to match JMTucker.
- **Fix:** Treat a negative refit chi2 as a failed refit: move on to the next track and keep the current vertex.
