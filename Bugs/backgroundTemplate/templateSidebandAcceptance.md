# The 3x4, 3x5 and 4x5 templates also take 7x7, 8x8 and 9x9 pairs, and their 5-track side differs from the observed regions.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:4012, 4017, 4027` (Alec's uncommitted 2026-11-05 version); the loop-2 copies at 4374-4393 never run. The last fill branch lacks `p.ntracks() <= 4`, so modes 7, 8 and 9 (3x4, 3x5 and 4x5) fill the template with 7x7, 8x8 and 9x9 pairs. The 3x5 and 4x5 branches take 5 or more tracks, while the observed 3x5 and 4x5 regions take exactly 5 (2500-2501 and the Ntk3or5exact and Ntk4or5exact trees), the cap of `Bugs/jmtucker/adapted/fiveTrackCappedAtFive.md`.
- **Kamui:** `backgroundTemplate/2v_from_jets.cc:745-749` (`passesTemplate`). Kept to match Alec's outputs.
- **Impact:** Minor: none of the 104,724 template entries in the lepton 3x4 run is a 7x7 trial. The 8x8, 9x9 and 5-track-side mismatches touch only the 3x5 and 4x5 templates, which the production runs never build.
- **Fix:** Limit the n x n line to 3x3, 4x4 and 5x5, and take 5 or more tracks on the observed side too (`Bugs/jmtucker/adapted/fiveTrackCappedAtFive.md`).
