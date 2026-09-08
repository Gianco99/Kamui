# Select

- The local pass is pure Python over the ntuples, uproot and awkward with no CMSSW, which is what lets a selection be iterated on in seconds. Condor jobs build a CMSSW area and `normalization.py` needs ROOT.
- The selection arrives already resolved. `normalization.py` is the one module here that opens a config file, `config/normalizations/generatorSums.json`.
- `engine.py`
    - One boolean mask accumulates and no row is dropped until the end, so every cut is evaluated on an index-aligned array and the cutflow is exact.
    - This stage removes events, never objects. An `object` cut is an existence test over a collection, and the objects that failed it stay in the file.
    - `_readAll` concatenates every input file into one in-memory array, which is what limits a pass. The local backend does no chunking, so `--filesPerJob` and `--dryRun` reach only the condor backend.
    - `_write` groups a collection's fields into one `ak.zip` record so uproot emits one counter per collection. Writing each jagged branch separately makes uproot invent `nElectron_pt`, `nElectron_eta` and so on.
    - `_primaryVertex` falls back to index 0 when no vertex passes `PV_isGood`. JMTucker drops those events, a known divergence no validation sample has hit.
    - `triggerMask` starts all-false and ORs in what it found, so a cut whose paths are all absent silently removes the whole sample. The `0/N paths present` note is the only sign, and it is where a wrong era or a missing skim shows up.
- `batch.py`
    - A submitted task is frozen. `prepare` ships `selection_<era>.json`, so editing a config afterwards changes nothing for queued jobs.
    - Its `taskDir` has no `resolveTaskDir` guard, so re-running an existing `--task` overwrites the job area silently. Memory and disk are arguments with no CLI flag.
    - `--outputBase` reaches only this backend. A local pass always writes under `ntupleSelection/out/<task>/`.
- `io.py`
    - `findInputs` hardcodes `<base>/ntuples/<inputTask>` on both branches, so chaining a pass onto an earlier pass's output means that output living under a directory named `ntuples`.
- `normalization.py`
    - Anything normalizing must call `denominator`, which returns `None` for a sample with no recorded sum.
