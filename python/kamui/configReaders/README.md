# ConfigReaders

Everything that turns a config file into something the code can use. Most readers here also resolve what they read: they follow every `include`, replace each definition name with its cuts, and keep only the values set for the era being run. The result is complete on its own, so a job never reads `config/` itself.

`catalog.py`: Reads the sample configs and answers "which samples do I mean".

`content.py`: Reads the content presets and works out what a job should write.

`selections.py`: Reads the selection configs that drive `select`.

`requirements.py`: Reads requirement lists. A requirement is a cut on one variable of an object, such as a jet's pT. Selections, definitions and the `VertexJet` collection all write requirements the same way.

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
    - A requirement in the `VertexJet` collection can only name a variable that the `Jet` collection in `jets.json` defines, since Kamui builds the C++ cut from that variable's expression in `Jet`.
- `selections.py`
    - With no era given, a threshold, trigger list or flag list set per era raises an error.
      - An `anyOf` alternative can name the `eras` it applies to. With an era given, the alternatives for other eras are dropped, and with no era every alternative is kept.
    - `CUT_TYPES` and `_cutMask` in `select/engine.py` must be kept in step.
- `sites.py`
    - Variables are filled in on the machine you submit from. On a worker node `$USER` is the batch account, so the output would go somewhere wrong.
