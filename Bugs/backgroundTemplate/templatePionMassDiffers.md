# The 1V mass cut takes the pion mass as 0.13957 GeV and the 2V mass cut as 0.1396 GeV.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:2989` (1V pool) and `3392, 3400` (observed 2V) (Alec's uncommitted 2026-11-05 version). A vertex right at the 5.5 GeV mass cut can pass one and fail the other.
- **Kamui:** No template code yet.
- **Rewrite:** `2v_from_jets.cc:56-58`. Kept to match Alec's outputs.
- **Impact:** Minor: the fix leaves the 1V pool and every template unchanged. In the observed 2V histograms it shifts each DV mass by 2e-5 to 1e-4 GeV, which flips far fewer than 0.01 expected events at the cut.
- **Fix:** Use one constant, 0.13957.
