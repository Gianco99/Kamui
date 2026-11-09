# The template measures the azimuths of its |dPhi| from each event's PV, and the observed |dPhi| measures them from the beamspot.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3028-3029` and `3862-3864` (template) against `3426-3427` (h_2v_absdphivv) (Alec's uncommitted version, snapshot of 2026-11-05). Comparing h_c1v_absdphivv_revertexed_w_errorbars with h_2v_absdphivv mixes the two frames. Neither feeds the limits.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:752-759` (`absDeltaPhi`).
- **Fix:** Measure both from the beamspot.
