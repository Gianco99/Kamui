# A constructed pair enters the template when exactly two vertices come back, with no tight DV cuts on them.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:371-433` (finish() returns only track counts and positions) and the fills at `4007` and `4369` (Alec's uncommitted version, snapshot of 2026-11-05). The tight cuts act on the input vertices only (`2992-2998`). Taking the leading two vertices instead adds 1 of 1,429 pairs in lepton and 9 of 6,578 in displacement; the effect of the missing tight cuts is not measured.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `2v_from_jets.cc:741-744` (`passesTemplate`).
- **Fix:** Apply the analysis 2V selection to the revertexed vertices: the tight cuts on each, then the two leading ones.
