# ConfigReaders

Everything that turns a config file into something the code can use.

`catalog.py`: Reads the sample configs and answers "which samples do I mean".

`content.py`: Reads the content presets and works out what a job should write.

`selections.py`: Reads the selection configs that drive `select`.

`requirements.py`: The per-object requirement grammar that selections, definitions and the vertexer's jets share.

`sites.py`: Reads `sites.json`, expanding the environment variables in it.

See `config/README.md` for the file formats, and `python/kamui/README.md` for the commands that drive all of this.

## Caveats

- Nothing outside this folder may open a config file.
    - `select/normalization.py` is the exception, reading and writing `generatorSums.json`.
    - `check` enforces this with a hand-kept list of `paths` names in `_cmdCheck`, so a new config directory has to be added to it.
- `catalog.py`
    - `--family`, `--era` and `--tag` resolve case-insensitively, `--name` is exact, `--match` is a glob.
- `content.py`
    - `KIND_TO_PLUGIN` maps a physics-facing `type` onto the CMSSW plugin that builds that table.
    - Content resolves against one era group, so a preset name has to exist in both trees.
    - A vertexJet requirement is translated to C++ through the `Jet` collection of `jets.json`, so it can only name a variable that collection defines.
- `selections.py`
    - With `era=None` an era-keyed threshold, trigger list or flag list raises.
      - `anyOf` is the exception: its era filter is skipped.
    - `CUT_TYPES` and the engine's `_cutMask` must be kept in step.
- `sites.py`
    - Variables expand on the submitting machine. On a worker node `$USER` is the batch account and the output would go somewhere wrong.
