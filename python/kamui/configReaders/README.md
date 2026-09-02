# configReaders/

Everything that turns a config file into something the code can use.

`catalog.py` - Reads the sample configs and answers "which samples do I mean". It expands grids into individual samples, then filters them by the selection flags you passed.

`content.py` - Reads the content presets and works out what a job should write. It flattens the include chain, drops the generator-level collections when the target is data, and turns the physics names you wrote into CMSSW-compatible language. It also reads the trigger configs, which is where a skim's HLT path list comes from.

`selections.py` - Reads the selection configs that drive `select`. It flattens the include chain, checks every key, cut type and quantity name, and resolves each era-dependent threshold, trigger list and flag list down to a single value for the era you asked for. What comes out is self-contained, so a worker never opens a config directory.

`sites.py` - Reads `sites.json`, which says where things are stored and which CMSSW release to use. Paths in there are written with `$USER`, filled in when the file is read, so the framework works for whoever runs it.
