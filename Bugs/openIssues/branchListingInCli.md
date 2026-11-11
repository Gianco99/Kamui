# The content branch listing `_branches` lives in `cli.py`, against the caveat that `cli.py` stays thin.

- **Where:** `python/kamui/cli.py:96-117`.
- **Problem:** `_branches` builds the CMSSW table producers and reads their parameters, which is behavior. The caveat in `python/kamui/README.md` limits `cli.py` to parsing, calling a module and printing, so the modules can be imported without the CLI.
- **Fix:** Move it beside `buildTables` (`ntupleProduction/cmssw/ntupleTables.py:192`).
