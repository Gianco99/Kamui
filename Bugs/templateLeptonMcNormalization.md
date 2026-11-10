# Lepton MC weights are normalized with MiniTree_tag001Lepm, while the events come from MiniTree_tag004Lepm.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets_new.py:18, 25, 32, 39` (sums of weights from tag001Lepm) and `2v_from_jets.cc:1467-1470` (events from tag004Lepm) (Alec's uncommitted version, snapshot of 2026-11-05). The event counts agree for 115 of 116 samples, so the effect is about 1% in one QCD sample.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: the rewrite calls the same helper, `2v_from_jets.cc:97-101` (`channels`) and `mcWeight`.
- **Fix:** Normalize from the production the events come from.
