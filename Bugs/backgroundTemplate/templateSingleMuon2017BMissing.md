# The lepton data list skips SingleMuon2017B.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:2465-2476`, and the 20% list at `2418-2429` (Alec's uncommitted 2026-11-05 version). The 2017 block reads SingleElectron2017B but no SingleMuon2017B, which `MiniTree_tag004Lepm4_unblind_5trk_1vtx` holds. It is the only one of the 34 lepton files left out; the displacement list reads 33 of 33.
- **Kamui:** No template code yet.
- **Rewrite:** `2v_from_jets.cc:133-134` (`sampleSets`). Kept to match Alec's outputs.
- **Effect:** Adding it moves the 4-bin template by up to 0.8 of its quoted error, within the pairing noise.
- **Impact:** Minor: the file adds 16 pairs to the 1,429, and most of the shift comes from reshuffling the random partner draws, so it is about the size of the pairing-seed spread of 0.4 to 0.8 of the quoted error.
- **Fix:** Add SingleMuon2017B to both lists.
