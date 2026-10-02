# ConfigReaders

Everything that turns a config file into something the code can use.

`catalog.py`: Reads the sample configs and answers "which samples do I mean".

`content.py`: Reads the content presets and works out what a job should write.

`selections.py`: Reads the selection configs that drive `select`.

`requirements.py`: Reads the per-object requirements, written the same way in selections, definitions and the vertexer's jets.

`sites.py`: Reads `sites.json`, expanding the environment variables in it.

See `config/README.md` for the file formats.

## Caveats

- Nothing outside this folder may open a config file.
    - `select/normalization.py` is the exception, reading and writing `generatorSums.json`.
    - `check` enforces this with a hand-kept list of `paths` names in `_cmdCheck`, so a new config directory has to be added to it.
- `catalog.py`
    - `--family`, `--era` and `--tag` ignore case, `--name` must match exactly, and `--match` takes a wildcard.
- `content.py`
    - `KIND_TO_PLUGIN` maps each collection's `type`, like `patJet`, to the CMSSW plugin that builds its table.
    - Run 2 and Run 3 samples read separate content files, so a preset both use needs a copy in each.
    - A `vertexJet` requirement can only name a variable that the `Jet` collection in `jets.json` defines, since its C++ cut is built from that collection.
- `selections.py`
    - With no era given, a threshold, trigger list or flag list set per era raises an error.
      - `anyOf` is the exception: with no era, it keeps every alternative.
    - `CUT_TYPES` and `_cutMask` in `select/engine.py` must be kept in step.
- `sites.py`
    - Variables are filled in on the machine you submit from. On a worker node `$USER` is the batch account, so the output would go somewhere wrong.
