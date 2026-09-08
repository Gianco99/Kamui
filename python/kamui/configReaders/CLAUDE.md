# ConfigReaders

- Nothing outside this folder may open a config file.
    - `select/normalization.py` is the exception, reading and writing `generatorSums.json`.
    - `check` enforces this against a hand-kept list of five names in `_cmdCheck`. `SELECTIONS_DIR` and `NORM_DIR` are missing from it.
- `catalog.py`
    - `--family`, `--era` and `--tag` resolve case-insensitively, `--name` is exact, `--match` is an unchecked glob.
    - Each resolves against the whole catalog, so `--family X --era Y` comes back empty when that era lives only in another family.
- `content.py`
    - `KIND_TO_PLUGIN` maps a physics-facing `type` onto the CMSSW plugin that builds that table.
    - Content resolves against one era group, so a preset name has to exist in both trees or half the catalog cannot reach it.
- `selections.py`
    - With `era=None` an era-keyed threshold, trigger list or flag list raises.
      - `anyOf` is the exception: its era filter is skipped, so every alternative survives.
    - `CUT_TYPES` and the engine's `_cutMask` must be kept in step.
    - Quantities are validated against `select.quantities.QUANTITIES`, which is why this module imports from `select/`. `quantities.py` imports nothing from kamui, so there is no cycle.
- `sites.py`
    - Variables expand on the submitting machine. On a worker node `$USER` is the batch account and output would go somewhere wrong.
