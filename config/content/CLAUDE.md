# config/content
## Caveats

- `--data` changes the answer, so every preset must work both ways. `check` resolves each one both ways.
- `collections/` is searched before `presets/`, so the two cannot share a name.
- An override states only the keys it changes, but naming `variables` throws away every variable the collection declared.
- `expr` is C++ evaluated at job runtime, so `check` cannot catch a typo. `bDiscriminator()` returns -1000 for a missing tagger, `electronID()` throws. `tools/inspectMiniAOD.py` lists what a file carries.
- `precision: -1` for anything a selection threshold compares against, including `vx`, `vy`, `vz` and the `PV` positions that impact parameters are recomputed from. Truncation quantizes pT enough to push an object onto a threshold.
- `GenPart` takes no `cut` and `PV` no `maxLen`. `genPartIdxMother` and `Track_pvIdx` index them positionally, so either one silently repoints every link.
- `maxLen` truncates in source order with no sort. Jets arrive pT-ordered, `SV` does not.
- Era copies are byte-compared. Editing one era's file alone fails `check` unless it is in `ERA_SPECIFIC_COLLECTIONS`.
