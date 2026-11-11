# Track-jet matching compares phi without wrapping, so a track and a jet track on either side of phi = pi never match.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:2168`. The phi factor is `fabs(tk.phi() - jtk->phi()) + 1`, so a track near phi = pi and a jet track near phi = -pi score as almost 2 pi apart, far above the 1.3 match threshold.
- **Kamui:** `vertexing/plugins/DVProducer.cc:215`. Reproduced on purpose to match JMTucker.
- **Impact:** Minor: a track that is itself a jet constituent matches its own copy with zero phi difference, so only tracks outside every jet can be affected. In 39.8k events the missing wrap changed one track's jet match and no DV.
- **Fix:** Use `reco::deltaPhi(tk.phi(), jtk.phi())` in the phi factor.
