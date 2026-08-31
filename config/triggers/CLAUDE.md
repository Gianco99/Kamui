# config/triggers
## Caveats

- Path order is JMTucker's, from `MFVNeutralino/python/TriggerFilter_cfi.py`. Do not sort.
- One list serves all four eras. A path absent from a year's menu never fires, so era-specific paths sit together in one list and `_pathsByEra` is the only record of which belongs where.
- `mode` and `process` are read by the production skim only. A selection cut takes `paths` alone, so `mode: "all"` would mean AND in production and OR in selection with nothing raising.
- `include` works, but `deepMerge` replaces lists, so a config cannot inherit `paths` and add one.
