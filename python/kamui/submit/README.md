# Submit

Everything that turns a set of samples into running jobs.

`common.py` - The parts both backends share: the task directory, the flattened content preset, the per-job file groups and `task.json`.

`condor.py` - The default backend. Runs at LPC, needs the file list up front, and has no automatic retries.

`crab.py` - For large productions. One CRAB task per sample, sent to sites that already hold the data.

See `ntupleProduction/README.md` for what a job area holds and where the output lands, and `python/kamui/README.md` for the commands that drive all of this.
