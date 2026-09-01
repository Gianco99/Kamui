# config/samples
## Where A Field's Value Comes From
`_loadFamily` and `_expandGrid` layer four things with increasing precedence: 

- `defaults`
- The grid's own fields or the explicit sample entry
- Any axis substitution whose key happens to be a sample field
- `overrides`. 

Ex: A grid that names `tags` throws away the `tags` in `defaults`, which is why every grid in `run2Validation.json` restates its family tags.

## JSON Caveats

- An axis whose name is a sample field sets that field on every point it generates,
  - An `era` axis makes those points selectable by era. 
  - An axis named anything else (ex:`mass` or `mStop`), only fills in the template.
- `era` has no default. A family that forgets `era` dies with a bare `KeyError`.
- `overrides` and `skip` are validated against the names the file actually generated.
  - Naming a sample asserts it exists, so an axis edit that renames one fails.

## Sample Caveats
Physics caveats per family are kept here so the configs stay readable.

**Exotic Higgs (exoticHiggs4d2024)**
- Run 3 ggH has no gen-HT filter, whereas the Run 2 samples had gen-HT > 200 GeV.
- ZH and WH are V-inclusive in Run 3 and were exclusive in Run 2.
- Summer24 does have exclusive ZH-Zto2L and WH-WtoLNu, and they are not in the catalog yet.

**RPV (rpv2024)**
- One private point from Bruno. Nothing exists in Run 3 for gluino to tbs or stop to bb, official or private.

**Stealth SUSY (stealthSusy2024)**
- Private from Bruno.
- Exclusive per (mStop, mSo, ctau).
- Inclusive samples exist for Run 2, but they are not in the catalog yet.

**Run 2 validation (run2Validation)**
- Dataset paths and event counts copied from JMTucker's `Tools/python/Samples.py` on 2026-08-25.
