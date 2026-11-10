# In 3x4, 3x5 and 4x5, only the b-tagged, npv <= 20 category rejects partners with the anchor's track count, and it can hang.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3633-3634` (Alec's uncommitted version, snapshot of 2026-11-05). The other seven categories (`3659`, `3681`, `3703`, `3725`, `3747`, `3769`, `3791`) reject only the vertex itself. If every vertex of that category has the anchor's track count, the redraw never ends.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces the veto on purpose (`2v_from_jets.cc:792-793`, `drawPartner`) and stops with an error where the original would hang (`803`).
- **Fix:** Apply one rule in every category, and check before drawing that an acceptable partner exists.
