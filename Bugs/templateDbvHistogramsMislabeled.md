# h_1v_dbv0 and h_1v_dbv1 are titled dBV but filled with the distance to the PV.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3024` and `3362-3363` (Alec's uncommitted version, snapshot of 2026-11-05). Anyone reading them as dBV shapes gets the distance from the PV in xy.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `2v_from_jets.cc:173-175` (`histogramSpecs`) and `423-424` (`fillOneVertexHistograms`).
- **Fix:** Fill them with dBV, or rename and retitle them.
