# ConfigReaders

This folder holds the code that turns a config file into something the rest of Kamui can use. Most readers here also resolve what they read: they follow every `include`, replace each definition name with its cuts, and keep only the values set for the era being run. The result is complete on its own, so a job never reads `config/` itself. For example, `resolveSelection("<selection>", era="<era>")` in `selections.py` returns the selection with all its cuts in one flat list, and every value that was set per era replaced by that era's value.

`catalog.py`: Reads the sample configs and answers "which samples do I mean".

`content.py`: Reads the content presets and works out what a job should write.

`selections.py`: Reads the selection configs that drive `select`.

`requirements.py`: Reads requirement lists. A requirement is a cut on one variable of an object, such as a jet's pT. Selections, definitions and the `VertexJet` collection all write requirements the same way.

`sites.py`: Reads `sites.json`, expanding the environment variables in it.

`normalizations.py`: Checks that every JSON file in `config/normalizations/` has the format its README describes, for `check`.

See `config/README.md` for the file formats.
