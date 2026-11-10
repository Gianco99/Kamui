# In MC, each category of the template is scaled by the mean event weight of its vertices.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3637`, `3659` and the other partner draws, and `3856` and `4304` (Alec's uncommitted version, snapshot of 2026-11-05). Partners are drawn uniformly and each pair fills with w0 times w1, so on average an anchor fills its own weight times its category's mean weight, and categories with heavier MC weights count more. Data has unit weights and is not affected.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `2v_from_jets.cc:765-766` (`fillPair`).
- **Fix:** Divide each pair's weight by the mean weight of its category, so each category enters with the summed weight of its anchors.
