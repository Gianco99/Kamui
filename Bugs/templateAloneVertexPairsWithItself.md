# A vertex alone in its category is paired with itself.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3630-3632`, its copies in the other categories, and `4135-4136` (Alec's uncommitted version, snapshot of 2026-11-05). With fewer than two candidates the redraw is skipped, so the anchor becomes its own partner and the revertexer fits its tracks twice; the "comparing track with itself!" messages in MC logs come from these pairs. Empty categories also build `uniform_int_distribution(0, -1)` (`3547-3555`, `4062-4069`). Harmless with full Run 2 statistics.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `2v_from_jets.cc:799-800` (`drawPartner`).
- **Fix:** Skip anchors that have no possible partner, or merge sparse categories.
