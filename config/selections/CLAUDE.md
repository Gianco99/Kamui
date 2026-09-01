# config/selections
## Caveats

- The two Run 2 configs are frozen against JMTucker, event for event, both channels, all four eras. Every threshold, working point, ladder and path list is load-bearing. A new study gets a new file.
- `leptonVeto` in `run2Displaced.json` is `run2Lepton.json`'s `leptonPlateau` legs with `invert: true`. The two channels are provably disjoint only while the two statements are the same statement, so a threshold that moves in one has to move in the other in the same edit. The invariant is that the two `anyOf` lists compare equal as JSON.
- Two things that look like omissions come from JMTucker: `Mu50`, `Ele115` and `Ele50_PFJet165` gate no leg, and `run2Lepton.json` carries no orthogonality veto of its own, because there the veto belongs to the displacement channel.
- A trigger pattern matching no branch makes `triggerMask` all-false, which kills the cut and the channel with it. The cutflow note reading `0/N paths present` is the only warning.
  - Flags fail the opposite way. A flag missing from the file is skipped and its events pass, so a misspelling makes the cut looser than written. The note appends `MISSING [...]`.
- `eras` is accepted on any cut by the validator but read only on an `anyOf` alternative. Anywhere else it validates and does nothing. Era-gate by wrapping in an alternative or by keying thresholds.
- `check` does not look at these files. `resolveSelection` is called only from `_cmdSelect`, so a broken config surfaces when someone runs `select`. Run one against a small sample after editing.
- A `veto` is already negated: it computes `~(fired & conditions)`, so adding `invert` hands back the events it exists to remove. It also needs an offline condition; a pure trigger veto is a `trigger` cut with `invert`.
- An `anyOf` requirement group is equivalent to separate legs only while the leg's `min` is 1. With `min: 2` a barrel-only plus an endcap-only object passes the folded form and fails the two-leg form. Nothing validates this.
- The per-alternative counts in an `anyOf` cut's note are over every input event with no upstream cut applied, so they do not sum to the cut's own `kept`. The `kept`, `removed` and `efficiency` columns themselves are properly sequential.
- Reader traps: a leg's `min` goes through a plain `int(...)`, so an era-keyed object there raises a `TypeError`. Thresholds become floats, so an integer ID is written `"min": 1`. `orderedMinPt` must be descending.
