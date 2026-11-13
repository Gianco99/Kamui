# In 5x5, the two pairing loops fix the mix of 4x>=5 and >=5x>=5 trials, whatever the 1V pool holds.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:2890-2892, 3583, 3637, 4059-4071, 4119` (Alec's uncommitted 2026-11-05 version). Loop 1 pairs each vertex with 5 or more tracks with any 4- or >=5-track vertex of its category, loop 2 pairs it again with a >=5-track vertex, and both fill at the same weight.
- **Kamui:** `backgroundTemplate/2v_from_jets.cc:812-822` (`pairingLoop`) and `896-898` (`runConfiguration`). Kept to match Alec's outputs.
- **Effect:** The 4x>=5 share comes out about 24 times below what random pairing of the 1V pool gives. The effect on the template is not measured yet: it needs trial and pass counts per input class.
- **Impact:** Changes physics results, by an amount not yet measured: in a simple model where a 4x>=5 trial passes 0.002 times as often as a >=5x>=5 one, random pairing raises bin 1 of the lepton limit template by about 3.4 of its quoted error, and the shift falls below 0.5 only when that ratio is under about 3e-4.
- **Fix:** Draw partners from the whole 1V pool so each input class enters at its own rate, or justify the fixed mix in the AN.
