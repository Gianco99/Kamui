# In 3x4, 3x5 and 4x5, only the b-tagged, npv <= 20 category rejects partners with the anchor's track count, and it can hang.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3633-3634` (Alec's uncommitted 2026-11-05 version). The other seven categories (3659, 3681, 3703, 3725, 3747, 3769, 3791) reject only the vertex itself. If every vertex of that category has the anchor's track count, the redraw never ends.
- **Kamui:** No template code yet.
- **Rewrite:** `2v_from_jets.cc:792-793` (`drawPartner`). Keeps the veto to match Alec's outputs, and stops with an error at 803 where the original would hang.
- **Impact:** Changes physics results: the b-tagged, npv <= 20 category supplies an estimated 80% of the lepton 3x4 template, against about 36% without the veto, and the AN takes its closure uncertainties from the 3x4 sideband. The 5x5 limit template is untouched.
- **Fix:** Apply one rule in every category, and check before drawing that an acceptable partner exists.
