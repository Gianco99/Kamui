# config

`README.txt` covers the layout and `sites.json`. Each subdirectory has its own pair of docs.

## Nothing Outside configReaders/ May Open These Files
`./kamui check` enforces it by scanning for direct use of the config path constants outside `python/kamui/configReaders/`. This is why `loadSites` lives in `configReaders/sites.py`.

## sites.json Is Expanded
String values pass through environment-variable expansion when loaded, which is how `$USER` works. Expansion happens on the submitting machine at config-load time, not on the worker node: `$USER` there would be the batch account and the output would go somewhere wrong. An unset variable raises rather than silently producing a path containing a literal `$`.

## Comment Keys Are Stripped At Every Depth
`loadSites` runs `stripComments`, so a `_doc` nested inside the `cmssw` block is dropped like any other.

## The Release Version
`cmssw.version` and `cmssw.scramArch` are read by the condor backend and written into every generated job script. Changing them changes what runs on the grid.
