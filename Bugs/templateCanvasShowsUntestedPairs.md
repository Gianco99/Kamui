# The sumdBV canvas overlays every constructed trial, before the template test, on the observed 2V shape.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:4523-4531` (Alec's uncommitted version, snapshot of 2026-11-05). The red curve is h_c1v_sumdbv_w_errorbars, which every trial fills; the template is h_c1v_sumdbv_revertexed_w_errorbars. Empty histograms are also scaled by 1/0.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:826-852` (`sumDbvCanvas`).
- **Fix:** Overlay h_c1v_sumdbv_revertexed_w_errorbars, and skip the scaling when a histogram is empty.
