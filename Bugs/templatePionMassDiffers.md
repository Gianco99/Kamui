# The 1V and 2V mass cuts take the pion mass as 0.13957 and 0.1396 GeV.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:2989` (1V pool, 0.13957) and `3392`, `3400` (observed 2V, 0.1396) (Alec's uncommitted version, snapshot of 2026-11-05). A vertex right at the 5.5 GeV mass cut can pass one and fail the other; the effect is tiny.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:56-58`.
- **Fix:** Use one constant, 0.13957.
