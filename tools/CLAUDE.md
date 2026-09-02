# tools
## triggerYields.py

- The denominator is already skimmed. Both presets it accepts declare `skim.triggers`, so every event in the file passed the channel OR and `eff` lands at essentially 100%. The number is a consistency check that the stored bits agree with the skim the job applied, not a trigger efficiency. `--perPath` is the informative output: it shows which paths carry the channel and which are absent from the era's menu.
- `mode` and `vetoes` are ignored. `yieldsFor` always joins paths with `||`, so a config saying `mode: "all"` would be silently ORed. The docstring promises a four-tuple ending in `nPassAfterVeto` and the function returns three values.
- `listEos` lists `<outLFNDirBase or outDirBase>/<sample>/` and takes every `.root`, the flat layout condor writes. A CRAB task records `outLFNDirBase` but nests its output below that level, so nothing is found. Use `--files` there.
- The regex on `--task` is a path-traversal guard, since the name is joined onto `JOBS_DIR`.
- No sample sets `notes`, so the `JMTucker reference:` line does not print today.

## inspectMiniAOD.py

- `--jets` defaults to `slimmedJetsPuppi`, which is the Run 3 collection. A Run 2 file needs `--jets slimmedJets` or the jet block reports nothing.
- Each collection is reported from the first event that has it, scanning up to `MAX_EVENTS`. A signal sample can easily have no electrons in event 1, and reporting only event 1 would read as "these IDs are not embedded".

## Both

- `tools/` sits outside `python/`, so each script inserts `python/` on `sys.path` to import kamui without the package being installed.
- Both need `cmsenv`, one for ROOT and one for FWLite. Neither is imported by kamui and neither runs as part of a job.
