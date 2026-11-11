# The b fraction f2 in the template weight is a placeholder, and the chain meant to measure it writes zeros.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3517, 4401-4404, 4731-4749` (Alec's uncommitted 2026-11-05 version). The revertexing method never increments `events_after_eff`, so every value in cb_vals.csv is 0, and `bquark_fraction.py` has no run2 labels. The only measured values, in `f2_vals.py` (2017 and 2018, from an older production), give f2 = 0.994 to 0.9996 for 5 tracks.
- **Kamui:** No template code yet.
- **Rewrite:** `2v_from_jets.cc:871-886` (`writeCbValues`). Writes the same zeros to match Alec's outputs.
- **Impact:** Changes physics results: with the integer division of `templateBtagWeightIntegerDivision.md` fixed, f2 = 0.99 moves the limit template by up to 0.6 of its quoted error in lepton and 0.1 in displacement, and f2 = f1 moves it by up to 9.6 and 2.5.
- **Fix:** Measure f2 for the revertexing method, per channel and per year if needed, and use it in the weight of `templateBtagWeightIntegerDivision.md`.
