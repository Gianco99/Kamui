# The 3x4, 3x5 and 4x5 templates also take pairs that come back as 7x7, 8x8 or 9x9, and the 5-track side of 3x5 and 4x5 differs from the observed regions.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:4012`, `4017` and `4027` (Alec's uncommitted version, snapshot of 2026-11-05) (the loop-2 copies at 4374-4393 never run). The last fill branch lacks `p.ntracks() <= 4`, so for ntracks 7, 8 and 9 a pair whose two vertices both have 7, 8 or 9 tracks fills the template. The 3x5 and 4x5 branches take 5 or more tracks, while the observed 3x5 and 4x5 regions take exactly 5 (`2500-2501` and the Ntk3or5exact and Ntk4or5exact trees), the cap of `fiveTrackCappedAtFive.md`.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `2v_from_jets.cc:745-749` (`passesTemplate`).
- **Fix:** Limit the n x n line to 3x3, 4x4 and 5x5, and take 5 or more tracks on the observed side too (`fiveTrackCappedAtFive.md`).
