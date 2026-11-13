# Select

This folder holds the code behind the `select`, `cutflow` and `norm` commands. A selection is an ordered list of event-level cuts from `config/selections/`. A selection pass applies a selection to the ntuples a `submit` task produced, and writes the events that pass every cut into new ntuples. Before a pass, Kamui resolves the selection for each era, replacing every value set per era with that era's value and every definition with its cuts.

For example, `./kamui select --tag <tag> --selection <selection> --task <passTask> --inputTask <ntupleTask>` runs a pass on this machine and writes the selected ntuples and their cutflow under `ntupleSelection/out/<passTask>/`, and `./kamui cutflow --task <passTask>` prints that cutflow. Add `--backend condor` to run the pass on condor instead, and see `python/kamui/README.md` for every flag.

When you run `./kamui select`, `io.py` plans the pass. A local pass then runs in `io.py`, which hands each sample to `engine.py`. With `--backend condor`, `batch.py` builds and submits the job area, and each job runs `job.py`, which calls the same engine.

`engine.py`: Applies a resolved selection to ntuples and writes ntuples with the same branches.

`io.py`: Plans a selection pass and runs it locally. It finds each sample's input ntuples, stops a pass that could not run, records the pass in `task.json`, and writes and prints the cutflow, adding up the per-job cutflows of a condor pass.

`batch.py`: Builds and submits the condor job area for a selection pass.

`job.py`: What each condor selection job runs, pushing one group of files through an already-resolved selection.

`normalization.py`: Measures and stores the generator sums a sample is normalized by. It is the only code outside `configReaders/` that reads or writes `config/normalizations/generatorSums.json`.

See `config/selections/README.md` for how a cut is written.

## Caveats

- Any code that normalizes must call `denominator` in `normalization.py`, which returns `None` for a sample with no recorded sum.
