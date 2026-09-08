# Select

Everything behind the `select`, `cutflow` and `norm` commands.

`engine.py` - Applies a resolved selection to ntuples and writes ntuples with the same branches.

`quantities.py` - The event-level quantities and the per-era jet identification a selection config may name.

`io.py` - Finds a production task's ntuples for a sample, and writes and prints the cutflow.

`batch.py` - Builds and submits the condor job area for a selection pass.

`runOne.py` - What a worker runs: one group of files through an already-resolved selection.

`normalization.py` - The generator sums a sample is normalized by, and the owner of `config/normalizations/generatorSums.json`.

See `config/selections/README.md` for how a cut is written, and `python/kamui/README.md` for the commands that drive all of this.
