# For ntracks 5 the observed 2V histograms take exactly 5x5 tracks, while the template takes 5 or more on each side.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:2498` sets min = max = 5 (Alec's uncommitted version, snapshot of 2026-11-05); the committed version 253d92111 kept 0 to 1000000. The bounds apply at `3362-3363` and `3382`. Data inputs are blinded, so this shows only in MC.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `2v_from_jets.cc:509-510` (`readInputs`).
- **Fix:** Take 5 or more tracks on the observed side, as the analysis does (`fiveTrackCappedAtFive.md`).
