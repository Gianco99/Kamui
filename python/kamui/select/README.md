# Select

Everything behind the `select`, `cutflow` and `norm` commands. A selection is an ordered list of event-level cuts from `config/selections/`. A selection pass applies a selection to the ntuples a `submit` task produced, and writes the events that pass every cut into new ntuples. Before a pass, Kamui resolves the selection for each era, replacing every value set per era with that era's value and every definition with its cuts.

`engine.py`: Applies a resolved selection to ntuples and writes ntuples with the same branches.

`io.py`: Finds a production task's ntuples for a sample, and writes and prints the cutflow.

`batch.py`: Builds and submits the condor job area for a selection pass.

`job.py`: What each condor selection job runs, pushing one group of files through an already-resolved selection.

`normalization.py`: Measures and stores the generator sums a sample is normalized by. It is the only code that reads or writes `config/normalizations/generatorSums.json`.

See `config/selections/README.md` for how a cut is written.

## Caveats

- The local pass is pure Python, so trying out a selection takes seconds.
  - Condor jobs build a CMSSW area, and `normalization.py` needs ROOT.
- `batch.py`
    - A submitted task is frozen: its jobs carry a copy of the selection, `selection_<era>.json`, so later config edits never reach them.
    - Reusing a `--task` name overwrites its job area without asking, since `select` never calls `resolveTaskDir`.
    - The memory and disk a condor selection job asks for are set in `batch.py`, and no CLI flag changes them.
    - `--outputBase` applies only to condor. A local pass writes under `ntupleSelection/out/<task>/`.
- `normalization.py`: any code that normalizes must call `denominator`, which returns `None` for a sample with no recorded sum.
