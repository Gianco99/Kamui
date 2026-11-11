# Select

This folder holds the code behind the `select`, `cutflow` and `norm` commands. A selection is an ordered list of event-level cuts from `config/selections/`. A selection pass applies a selection to the ntuples a `submit` task produced, and writes the events that pass every cut into new ntuples. Before a pass, Kamui resolves the selection for each era, replacing every value set per era with that era's value and every definition with its cuts.

When you run `./kamui select`, `io.py` plans the pass. A local pass then runs in `io.py`, which hands each sample to `engine.py`. With `--backend condor`, `batch.py` builds and submits the job area, and each job runs `job.py`, which calls the same engine.

`engine.py`: Applies a resolved selection to ntuples and writes ntuples with the same branches.

`io.py`: Plans a selection pass and runs it locally. It finds each sample's input ntuples, stops a pass that could not run, records the pass in `task.json`, and writes and prints the cutflow, adding up the per-job cutflows of a condor pass.

`batch.py`: Builds and submits the condor job area for a selection pass.

`job.py`: What each condor selection job runs, pushing one group of files through an already-resolved selection.

`normalization.py`: Measures and stores the generator sums a sample is normalized by. It is the only code outside `configReaders/` that reads or writes `config/normalizations/generatorSums.json`.

See `config/selections/README.md` for how a cut is written.

## Caveats

- The local pass is pure Python, so trying out a selection takes seconds.
  - Condor jobs build a CMSSW area, and `normalization.py` needs ROOT.
- A task name belongs to one pass, since a second pass under it would mix its outputs and cutflow with the first one's. `select` refuses a name that a production task already uses, or that has local outputs, a submitted condor job area or files in its EOS output directory. It rebuilds a condor job area that was never submitted, such as one a dry run left.
- `engine.py`
    - A pass reads all of a sample's files as one, and a condor job all of its own files. If the files come from different HLT menus, a trigger or flag decision that a file does not have counts as not fired in that file's events, and the selected ntuples keep every decision any file had. Every other branch must be in every file, or the pass stops and names the two files that differ.
- `io.py`
    - Condor jobs read their inputs over xrootd, so a condor pass refuses a local `--inputBase`.
- `batch.py`
    - A submitted task is frozen: its jobs carry their own copy of the selection, `selection_<era>.json`, so later config edits never reach them.
    - A condor selection job asks for the memory `--memoryMB` gives, or `DEFAULT_MEMORY_MB` without the flag. The disk it asks for is set in `batch.py`, and no flag changes it.
    - `--outputBase` applies only to condor. A local pass writes under `ntupleSelection/out/<task>/`.
- `normalization.py`
    - Any code that normalizes must call `denominator`, which returns `None` for a sample with no recorded sum.
    - Several `./kamui norm --write` runs can run at once. Each one waits its turn on `generatorSums.json.lock`, then reads `generatorSums.json` again before adding its entries, so no run loses another's.
