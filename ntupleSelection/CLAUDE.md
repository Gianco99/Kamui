# ntupleSelection

Applying an event selection to production ntuples. The code is in `python/kamui/select/`; the human-facing description of the stage is `README.md` here.

## Layout

`out/` and `jobs/` are generated and gitignored, so the docs are the only tracked content in this directory and a fresh clone contains neither. Every writer makes its own directory: `batch.taskDir` for a job area, `io.writeCutflow` for a cutflow, `engine._write` for the output file itself. Nothing checks that these directories exist, nothing needs a `.gitkeep`, and a missing `out/` is not a broken checkout.

## The resolved selection travels to the worker as JSON

`resolveSelection` flattens the config, picks the era's value for every threshold, trigger list and flag list, and expands a trigger config name into the explicit list of HLT paths. `batch.prepare` dumps the result to `selection_<era>.json` in the job area and lists it in `transfer_input_files`; `runOne.py` loads that file and hands it straight to `applySelection`. A worker therefore never reads `config/`, neither `config/selections/` nor `config/triggers/`, and needs no repository checkout at all: `kamuiPackage.tar.gz` carries `python/kamui` and the job puts it on `PYTHONPATH`.

The consequence is that a submitted task is frozen. Editing a selection config after `prepare` has run changes nothing about jobs already in the queue, and rebuilding the job area is the only way to pick the edit up.

The job still runs `scramv1 project CMSSW` from cvmfs to get a python3 carrying uproot and awkward.

## Era plumbing

`selection["era"]` is set when the selection is resolved and travels inside the JSON. `applySelection` reads it back out with `selection.get("era")` and passes it to every cut. It reaches the jet identification: `quantities.tightLepVeto` picks the 2016 working point or the 2017/18 one from the era and raises for anything else, so every quantity built on identified jets (`HT40`, `HT30`, `nJet20`, `nJet40`) is era-dependent. A selection resolved without an era survives resolution and then dies the first time such a quantity is evaluated, which is why the CLI never resolves one without an era.

Because thresholds and trigger lists differ by year, `_cmdSelect` resolves one selection per era among the samples it was given. On condor that becomes one `selection_<era>.json` and one `runSelect_<selection>_<era>.sh` per era, and each row of `jobList.txt` names the script matching its own sample's era. Adding an era means the selection config has to define values for it and `quantities.tightLepVeto` has to know its jet identification; the Run 3 table is still open in `docs/JetID.txt`.

## Things That Will Bite

- **A trigger cut whose paths are all absent keeps nothing.** `triggerMask` starts from all-false and ORs in the branches it found, so a missing path list silently removes the sample. The `applied as` line in the cutflow reporting `0/N paths present` is the only sign. A `flags` cut reports the flags it could not find and applies the rest.
- **Everything is read into memory at once.** `_readAll` concatenates every input file into one array before the first cut. `--filesPerJob` is the memory knob on condor; a local pass over a whole sample loads that whole sample.
- **`--outputBase` reaches only the condor backend.** The local backend always writes under `ntupleSelection/out/<task>/`.
- **Re-running with an existing `--task` overwrites the job area silently.** `batch.taskDir` is a plain `makedirs`. The `resolveTaskDir` guard that protects a production area, with its prompt and its refusal to clobber a running task, is not on this path.
- **`checkTaskName` runs only on the condor path**, inside `batch.taskDir`. The local path joins `--task` into `out/` directly.
- **`findInputs` always looks under `<base>/ntuples/<inputTask>`.** The path component is hardcoded for both the local-directory and the xrootd branch. Repeating the stage on a previous pass's output means that output living under a directory named `ntuples`.
- **The sample name has to appear as a whole path component** of a file's directory. `..._2016` is a prefix of `..._2016APV`, so substring matching would let one sample claim the other's files.
- **`_write` groups a collection only when the file carries both an `nX` counter and `X_` fields.** That grouping is what makes the output schema identical to the input schema and the stage repeatable. A jagged branch arriving without its counter gets one invented by uproot under a derived name, and the schema stops repeating from that point on.
- **`root://` inputs are copied local with `xrdcp` before being opened.** uproot needs fsspec-xrootd to read a URL directly and the CMSSW python stack does not ship it, so both the worker and an interactive session go through `_localCopy` into the system temporary directory.
- **`./kamui cutflow` reads only the local `out/<task>/cutflow.json`.** A condor pass writes one `<sample>_cutflow_<index>.json` per job to EOS and there is no merge step, so the command has nothing to print after a condor run.

## Normalization

`normalization.py` sits in this stage but writes into `config/crossSections/generatorSums.json`, because the sums belong to the dataset as DAS defines it, whatever subset a job happened to read. `record` compares the measured event count with the DAS one and stores `complete`; `denominator` raises on an entry marked incomplete, since a partial sum inflates every yield built on it. Measure over a full production, never over a capped file list.
