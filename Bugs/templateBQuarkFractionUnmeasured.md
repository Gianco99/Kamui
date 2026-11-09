# The b fraction f2 of the template weight is a placeholder, and the chain meant to measure it writes zeros.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3517`, `4401-4404` and `4731-4749` (Alec's uncommitted version, snapshot of 2026-11-05). `events_after_eff` is never incremented since revertexing replaced the pair efficiencies, so every value in cb_vals.csv is 0, and `bquark_fraction.py` has no run2 labels. The only measured values, in `f2_vals.py` (2017 and 2018, an older production), give f2 = 0.994 to 0.9996 for 5 tracks.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:871-886` (`writeCbValues`) writes the same zeros.
- **Fix:** Measure f2 for the revertexing method, per channel and per year if needed, and use it in the weight of `templateBtagWeightIntegerDivision.md`.
