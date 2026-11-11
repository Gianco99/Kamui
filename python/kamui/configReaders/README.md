# ConfigReaders

This folder holds the code that turns a config file into something the rest of Kamui can use. Most readers here also resolve what they read: they follow every `include`, replace each definition name with its cuts, and keep only the values set for the era being run. The result is complete on its own, so a job never reads `config/` itself. For example, `resolveSelection("<selection>", era="<era>")` in `selections.py` returns the selection with all its cuts in one flat list, and every value that was set per era replaced by that era's value.

`catalog.py`: Reads the sample configs and answers "which samples do I mean".

`content.py`: Reads the content presets and works out what a job should write.

`selections.py`: Reads the selection configs that drive `select`.

`requirements.py`: Reads requirement lists. A requirement is a cut on one variable of an object, such as a jet's pT. Selections, definitions and the `VertexJet` collection all write requirements the same way.

`sites.py`: Reads `sites.json`, expanding the environment variables in it.

`normalizations.py`: Checks that every JSON file in `config/normalizations/` has the format its README describes, for `check`.

See `config/README.md` for the file formats.

## Caveats

- Nothing outside this folder may open a config file.
    - The exception is `select/normalization.py`, which reads and writes `generatorSums.json`.
- `catalog.py`
    - `--family`, `--era` and `--tag` ignore case, `--name` must match exactly, and `--match` takes a wildcard.
    - An unknown sample, family, era or tag raises a `ValueError` whose message suggests known names that look close.
    - Every sample must set `isMC`. For a central dataset, Kamui checks it against the dataset tier: `MINIAODSIM` means MC and `MINIAOD` means data. Kamui never checks a USER dataset, so make sure its `isMC` is right.
- `content.py`
    - `KIND_TO_PLUGIN` maps each collection's `type`, such as `patJet`, to the CMSSW plugin that builds its table.
    - Run 2 and Run 3 samples read separate content files, so a preset both runs use needs a copy in each.
    - A requirement in the `VertexJet` collection can only name a variable that the `Jet` collection in `jets.json` defines, because Kamui builds the C++ cut from that variable's expression in `Jet`.
    - `loadTriggerConfig` is the only reader of trigger files, so the skim, selection trigger cuts, `check` and `tools/triggerYields.py` all apply the same rules.
      - When a file keys its paths by era, it reads them with the era it is given, and stops on an era the file does not list or when it is given no era at all.
- `selections.py`
    - Without an era, a threshold, trigger list or flag list set per era raises an error.
      - An `anyOf` alternative can name the `eras` it applies to. Given an era, Kamui drops the alternatives for other eras. Given no era, it keeps every alternative.
    - `CUT_RESOLVERS` lists each cut type with the fields it takes and the function that resolves it, and `CUT_TYPES` is built from it. `select/engine.py` stops on import when `CUT_TYPES` and the keys of its `CUT_MASKS` differ, so a new cut type needs an engine function too.
    - An `object` cut with `max` becomes a `quantity` count, since the engine bounds only counts from above.
    - A selection that asks for the signal region, as `SIGNAL_REGION` describes it, must say `"blind": true`, or resolving it fails. Kamui spots this only from a count of `DV` objects with an `nTracks` lower bound, after definitions are expanded, so a DV count read from an event branch slips past. It also looks only at what a selection asks for, so a two-DV control region can still keep a data event that also holds two signal-region DVs.
- `sites.py`
    - Kamui fills in the variables on the machine you submit from. On a worker node `$USER` is the batch account, so filling them in there would send the output somewhere wrong.
