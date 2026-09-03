# Selection Caveats

- A trigger pattern matching no branch makes `triggerMask` all-false, which kills the cut and the channel with it.
- `eras` is accepted on any cut by the validator but is only used on an `anyOf` alternative.
- An `anyOf` requirement group is equivalent to separate legs only while the leg's `min` is 1.

## Per-File Caveats

**Both Run 2 configs**
- Frozen against JMTucker on September 3rd 2026.

**run2Displaced.json**
- `leptonVeto` is `run2Lepton.json`'s `leptonPlateau` legs inverted. The two channels are disjoint only while the two lists compare equal as JSON, so a threshold that moves in one has to move in the other in the same edit.

**run2Lepton.json**
- Carries no orthogonality veto of its own, because in JMTucker the veto is only used in the displacement channel.
