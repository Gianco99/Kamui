# A constructed pair enters the template whenever revertexing returns exactly two vertices, with no tight DV cuts on them.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:371-433, 4007, 4369` (Alec's uncommitted 2026-11-05 version). `finish()` returns only track counts and positions, and the fills at 4007 and 4369 test only those. The tight cuts act on the input vertices alone (2992-2998).
- **Kamui:** `backgroundTemplate/2v_from_jets.cc:741-744` (`passesTemplate`). Kept to match Alec's outputs.
- **Effect:** Taking the two leading vertices instead adds 1 of 1,429 pairs in lepton and 9 of 6,578 in displacement. The effect of the missing tight cuts is not measured.
- **Impact:** Changes physics results, by an amount not yet measured: only pairs whose track sets changed in revertexing can fail the tight cuts, and that is common (23% of accepted lepton pairs have an output vertex with 6 or more tracks), but nothing records their share of the limit template.
- **Fix:** Apply the analysis 2V selection to the revertexed vertices: the tight cuts on each, then the two leading ones.
