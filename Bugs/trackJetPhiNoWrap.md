# Track-jet matching compares phi without wrapping, so a track and a jet on either side of pi never match.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:2168`. The phi factor is `fabs(tk.phi() - jtk->phi()) + 1`, so a track near phi = pi and a jet track near phi = -pi score as almost 2 pi apart, far above the 1.3 match threshold.
- **Kamui:** `vertexing/plugins/DVProducer.cc:190`. Reproduced on purpose to match JMTucker.
- **Fix:** Use `reco::deltaPhi(tk.phi(), jtk.phi())` in the phi factor.
