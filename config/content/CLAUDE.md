# Content Caveats
- `collections/` is searched before `presets/`, so the two cannot share a name.
- `expr` is C++ evaluated at job runtime, so `check` cannot catch a typo.
- `precision: -1` for anything a selection threshold compares against, including `vx`, `vy`, `vz` and the `PV` positions that impact parameters are recomputed from. Truncation quantizes pT enough to push an object onto a threshold.
- `GenPart` takes no `cut` and `PV` no `maxLen`. `genPartIdxMother` and `Track_pvIdx` index them positionally.
- `maxLen` truncates in source order with no sort. Jets arrive pT-ordered, `SV` does not.
