# The template's per-bin errors treat every constructed pair as independent, but each vertex is reused, so they understate the statistical error.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:3515, 3583, 4071, 4631` (Alec's uncommitted 2026-11-05 version). Each anchor gets one random partner, each vertex with 5 or more tracks is used about 2.2 times, and the errors are plain Sumw2.
- **Kamui:** No template code yet.
- **Rewrite:** `2v_from_jets.cc:812-822` (`pairingLoop`) and `896-898` (`runConfiguration`). Kept to match Alec's outputs.
- **Effect:** Changing only the two pairing seeds moves the 4-bin fractions by 0.4 to 0.8 of the quoted error in lepton and 0.5 to 1.0 in displacement (RMS over 5 seeds). That spread is expected from the random partner choice.
- **Impact:** Minor: the true error is estimated at up to about 1.6 times the quoted one, and the background uncertainty in the datacards is dominated by the normalization and closure terms. Scaling the statistical term by 1.6 raises the total in lepton bin 1 from 19.8% to 21.7% and moves the displacement bins by 0.2 percentage points or less.
- **Fix:** Draw K partners per anchor with weight 1/K, and take the per-bin errors from a bootstrap over the 1V vertices.
