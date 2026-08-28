# config

`README.md` covers the layout, `sites.json` and `lumi.json`. `samples/`, `content/`, `triggers/` and `crossSections/` each have their own pair of docs; `selections/` has a README only.

## Nothing Outside configReaders/ May Open These Files
`./kamui check` enforces it by scanning every `.py` outside `python/kamui/configReaders/` for `paths.CONFIG_DIR`, `paths.SAMPLES_DIR`, `paths.CONTENT_DIR`, `paths.TRIGGERS_DIR` and `paths.SITES_FILE`. This is why `loadSites` lives in `configReaders/sites.py`.

The scan list has not grown with the directory. `SELECTIONS_DIR`, `XSEC_DIR` and `LUMI_FILE` are absent from it, and `select/normalization.py` opens `XSEC_DIR` directly as a result. Adding those constants to the check will flag that file, so move its file access into `configReaders/` in the same change.

## sites.json Is Expanded
String values pass through environment-variable expansion when loaded, which is how `$USER` works. Expansion happens on the submitting machine at config-load time, not on the worker node: `$USER` there would be the batch account and the output would go somewhere wrong. An unset variable raises rather than silently producing a path containing a literal `$`.

## Comment Keys Are Stripped At Every Depth
`loadSites` runs `stripComments`, so a `_doc` nested inside the `cmssw` block is dropped like any other.

## The Release Version
`cmssw.version` and `cmssw.scramArch` are read by the condor backend and written into every generated job script. Changing them changes what runs on the grid.

## The Two Stageout Bases
CRAB refuses an `outLFNDirBase` under another user's `/store/user` area, so it cannot write to the shared `lpcdisplacedvertices` directory and gets its own `crabStageoutBase`. Condor stages out with `xrdcp` and has no such restriction, so it keeps the group area. `--outputBase` overrides either.

## lumi.json Has No Reader
`paths.LUMI_FILE` points at it and nothing opens it. The numbers are looked up by hand while a normalization step is being written, so the underscore keys in it are read by people and are not stripped by anything.

## The lumi.json Era Keys Are Campaign Names
`Summer22` is 2022 pre-EE alone and `Summer23` is 2023 pre-BPix alone; the rest of those years lives under `Summer22EE` and `Summer23BPix`. Summing a year means summing two keys. `Summer24` is the whole year with no intra-year split, matching the campaign.

## Why channels.displaced Stops At Run 2
It holds 2017 and 2018 only because those are the years the b-jet triggers were partly live. There is no Run 3 entry because `triggers/` has no Run 3 channel yet; add the trigger list first, then the channel luminosity.
