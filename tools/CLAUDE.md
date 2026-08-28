# tools

`README.md` says what `triggerYields.py` does and how to run it. This is what to be careful about.

## The Denominator Is Already Skimmed
The content presets this script accepts (`dvDisplaced`, `dvLepton`) declare `skim.triggers`, and `kamuiNtuple_cfg.py` gives the output module `SelectEvents` on the skim path. Every event in the file therefore already passed the channel OR, so `total` is the post-skim count and `eff` lands at essentially 100%. The number is a consistency check that the stored trigger bits agree with the skim the job applied, not a trigger efficiency. The genuinely informative output is `--perPath`, which shows which paths carry the channel and which are absent from the era's menu. The pre-skim event count is not in the `Events` tree and this script never reads it.

## Mode and Vetoes Are Ignored
`yieldsFor` always joins the paths with `||`. A trigger config's `mode: "all"` would be silently treated as an OR; both current configs say `any`. The `vetoes` blocks are not applied either: the docstring promises a four-tuple ending in `nPassAfterVeto`, and the function returns three values. If vetoes are ever implemented in the job, this is one of the places that has to follow.

## Where It Looks For Files
`listEos` lists `<outLFNDirBase or outDirBase>/<sample>/` and takes every `.root`, which is the flat layout the condor backend writes. Two consequences: a CRAB task records `outLFNDirBase` but CRAB nests its output below that level, so nothing is found; and a task submitted with `output=both` leaves `<sample>_ntuple_<i>.root` and `<sample>_miniaod_<i>.root` side by side in that directory, both of which have an `Events` tree, so the chain picks up both and `total` roughly doubles. Use `--files` for either case.

## Small Things
- The `sys.path` insert at the top is there because `tools/` sits outside `python/` and the script is run straight from the repo without the package being installed.
- The regex on `--task` is a path-traversal guard, since the name is joined onto `JOBS_DIR`.
- `select` is imported from `configReaders.catalog` and never used.
- No sample in `config/samples/` currently sets `notes`, so the `JMTucker reference:` line does not print today.
