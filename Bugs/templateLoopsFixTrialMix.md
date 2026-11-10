# In 5x5, the two pairing loops fix the mix of 4x>=5 and >=5x>=5 trials, whatever the 1V pool holds.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:2890-2892`, `3583`, `3637`, `4059-4071` and `4119` (Alec's uncommitted version, snapshot of 2026-11-05). Loop 1 pairs each vertex with 5 or more tracks with any 4- or >=5-track vertex of its category, loop 2 pairs it again with a >=5-track vertex, and both fill at the same weight. The 4x>=5 share comes out about 24 times below what random pairing of the 1V pool gives. The effect on the template is not measured yet: it needs trial and pass counts per input class.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `2v_from_jets.cc:896-898` (`runConfiguration`) and `812-822` (`pairingLoop`).
- **Fix:** Draw partners from the whole 1V pool so each input class enters at its own rate, or justify the fixed mix in the AN.
