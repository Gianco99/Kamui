# ConfigReaders

Everything that turns a config file into something the code can use. Most readers here also resolve what they read: they follow every `include`, replace each definition name with its cuts, and keep only the values set for the era being run. The result is complete on its own, so a job never reads `config/` itself.

`catalog.py`: Reads the sample configs and answers "which samples do I mean".

`content.py`: Reads the content presets and works out what a job should write.

`selections.py`: Reads the selection configs that drive `select`.

`requirements.py`: Reads requirement lists. A requirement is a cut on one variable of an object, such as a jet's pT. Selections, definitions and the `VertexJet` collection all write requirements the same way.

`sites.py`: Reads `sites.json`, expanding the environment variables in it.

`normalizations.py`: Checks that every file in `config/normalizations/` has the format its README describes, for `check`.

See `config/README.md` for the file formats.

## Caveats

- Nothing outside this folder may open a config file.
    - `select/normalization.py` is the exception, reading and writing `generatorSums.json`.
- `catalog.py`
    - `--family`, `--era` and `--tag` ignore case, `--name` must match exactly, and `--match` takes a wildcard.
    - `isMC` is required, and Kamui compares it with the tier of a central dataset, `MINIAODSIM` for MC and `MINIAOD` for data. A USER dataset is never compared, so its `isMC` has to be right.
- `content.py`
    - `KIND_TO_PLUGIN` maps each collection's `type`, like `patJet`, to the CMSSW plugin that builds its table.
    - Run 2 and Run 3 samples read separate content files, so a preset both use needs a copy in each.
    - A requirement in the `VertexJet` collection can only name a variable that the `Jet` collection in `jets.json` defines, since Kamui builds the C++ cut from that variable's expression in `Jet`.
    - `loadTriggerConfig` is the one reader of trigger files, so the skim, selection trigger cuts and `check` all apply the same rules.
- `selections.py`
    - With no era given, a threshold, trigger list or flag list set per era raises an error.
      - An `anyOf` alternative can name the `eras` it applies to. With an era given, the alternatives for other eras are dropped, and with no era every alternative is kept.
    - `CUT_RESOLVERS` lists each cut type with the fields it takes and the function that resolves it, and `CUT_TYPES` comes from it. `select/engine.py` stops on import when `CUT_TYPES` and the keys of its `CUT_MASKS` differ, so a new cut type needs an engine function too.
    - An `object` cut with `max` is turned into a `quantity` count, since the engine bounds only counts from above.
    - A selection that asks for the signal region, as `SIGNAL_REGION` describes it, has to say `"blind": true`, or resolving it fails. Kamui spots this only from a count of `DV` objects with an `nTracks` lower bound, after definitions are expanded, so a DV count read from an event branch slips past. It also looks only at what a selection asks for, so a two-DV control region can still keep a data event that holds two signal-region DVs as well.
- `sites.py`
    - Variables are filled in on the machine you submit from. On a worker node `$USER` is the batch account, so the output would go somewhere wrong.
