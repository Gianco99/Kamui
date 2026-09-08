# NtupleProduction

- Nothing in `cmssw/` may import from `python/kamui`. Only those two files, the resolved content JSON and `fileLists.json` reach a worker, so an import from the package breaks every job at once.
- The gen-weight table is picked out by substring: `normNames` matches `"genweight"` against a module name built from the collection key. Renaming `genWeight` in `config/content/*/collections/gen.json` silently moves the weights inside the skim path, where a skimmed job would undercount them.
- The tables run as a `cms.Task`, so a producer whose product no `outputCommands` keep pattern matches never runs at all.
- The CMSSW release in `config/sites.json` is what condor builds. Do not bump it without checking. CRAB ignores it and ships the release you submit from.
- The schedd is recorded at submit time. LPC spreads a submission across schedds and `condor_q` asks the default one, so a task submitted elsewhere reads as finished. A `task.json` with no `schedd` key falls back to the default.
