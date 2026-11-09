# The lepton data list skips SingleMuon2017B.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:2465-2476`, and the 20% list at `2418-2429` (Alec's uncommitted version, snapshot of 2026-11-05). The 2017 block reads SingleElectron2017B and no SingleMuon2017B, which `MiniTree_tag004Lepm4_unblind_5trk_1vtx` holds. It is the only one of the 34 lepton files left out (the b-jet list reads 33 of 33). Adding it moves the 4-bin template by up to 0.8 of its quoted error, within the pairing noise.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:133-134` (`sampleSets`).
- **Fix:** Add SingleMuon2017B to both lists.
