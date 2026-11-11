# The b-composition weight of a constructed pair uses integer division, so b-tagged pairs weigh 1 and untagged pairs weigh 0.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3917-3923, 4323-4329` (Alec's uncommitted 2026-11-05 version). `btag_weight = 99/80` and `1/20` stand for f2/f1 and (1 - f2)/(1 - f1) with the placeholders f2 = 0.99 and f1 = 0.80. Every pair with an untagged anchor drops out, and the nobtags output is empty.
- **Kamui:** No template code yet.
- **Rewrite:** `2v_from_jets.cc:762-764` (`fillPair`). Kept to match Alec's outputs.
- **Effect:** 759 of 2,188 pairs drop out in the lepton channel and 413 of 6,991 in the displacement channel. Float division moves the 4-bin template by up to 0.6 of its quoted error in lepton and 0.1 in displacement, while unit weights move it by up to 9.6 and 2.5, so the template depends strongly on f2.
- **Impact:** Changes physics results: the limit template is built from b-tagged pairs only, as if f2 = 1, so no measured f2 can take effect. The 3x3, 3x4 and 4x4 sideband templates that set the closure uncertainties come out b-tagged only too, while the old measurement gives f2 = 0.22 to 0.87 for those track counts.
- **Fix:** Use floating point, with f2 measured for this method (`templateBQuarkFractionUnmeasured.md`) and f1 from the 1V pool (71.5% lepton, 90.1% displacement).
