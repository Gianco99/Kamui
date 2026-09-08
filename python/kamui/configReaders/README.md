# ConfigReaders

Everything that turns a config file into something the code can use.

`catalog.py` - Reads the sample configs and answers "which samples do I mean".

`content.py` - Reads the content presets and works out what a job should write.

`selections.py` - Reads the selection configs that drive `select`.

`sites.py` - Reads `sites.json`, expanding the environment variables in it.

See `config/README.md` for the file formats, and `python/kamui/README.md` for the commands that drive all of this.
