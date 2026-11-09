# A shared-jet refit that fails leaves an empty vertex, which the next sweep drops.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1916-1921, 1937-1940`. `sv0_resolved_sharedtracks` starts as a default `reco::Vertex` and gets a fit only when `kv_reco_dropin` returns one, yet `sv0` is overwritten with it either way. The trackless vertex fails every later `nTracks() > 2` test and the cleanup loop erases it at 1940, so a vertex that should lose one lone track loses all its tracks.
- **Kamui:** `vertexing/plugins/DVProducer.cc:479-481, 487-488`. Reproduced on purpose to match JMTucker: the `fitVertex` result is ignored and `sv0` takes the default vertex.
- **Fix:** Overwrite `sv0` only when the refit succeeds, and keep the previous vertex when it fails.
