# Trigger Caveats
- Path order inspired by JMTucker's, from `MFVNeutralino/python/TriggerFilter_cfi.py`.
- `_pathsByEra` is the only record of which path belongs to which year's menu.
- `mode` and `process` reach the production skim only. A selection cut takes `paths` alone, so `mode: "all"` would mean AND in production, but OR in selection.
