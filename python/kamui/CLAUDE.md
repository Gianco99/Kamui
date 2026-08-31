# Kamui

## Design Premise
- Kamui is the CLI for the whole analysis framework.
- Two stages exist: sample processing (`submit`) and event selection (`select`).
- When a new stage is added it belongs here as commands.

The design principle the whole package serves is that the physics lives in configuration files and this code only executes what they say.
## Main Driver - cli.py
- Every command lives in this one file. 
  - Adding one is two edits here: a `_cmdX` handler, and an `_addCmd(sub, ...)` block that points at it. 
  - Registration order is the order `--help` lists them, and it follows the root README's command table.
- Keep it thin. It parses, calls a module, and prints. The actual behavior belongs in the modules so they can be imported without the CLI.
## The Basics - foundations/
- Nothing here may import from anywhere else in kamui.
- `paths.py` is the only module allowed to know the repository layout. Anything else that hardcodes a directory name is a bug, and moving a directory should mean editing this file alone.
    - It derives the repository root from its own file location, which is why the package can be moved without configuration. That also means it breaks silently if the file is relocated without updating the `dirname` chain.
- `config.py` merges layer by layer, and a list replaces the list below.
    - For example: `dvLepton` is built on `dvDisplaced` and swaps its 11 displacement HLT paths for 8 lepton ones.
    - The cost falls on two keys where adding is the natural intent: `miniaod.keep`, restated in full by `dvBase`, `dvSignal` and `dvFull`, and `tags`, restated by all three grids in `run2Validation`. If that becomes annoying, add an opt-in append marker to `deepMerge`.


## Reading the Configs - configReaders/
- Nothing outside this folder may open a config file.
    - `./kamui check` enforces it by scanning for `paths.*_DIR` and `paths.SITES_FILE` outside `configReaders/`.
    - This is why `loadSites` lives here, and why `_cmdCheck` calls `validateTriggers()` to reach the trigger directory.
    - `select/normalization.py` is the one place that writes a config file, `config/normalizations/generatorSums.json`. It is measured data rather than hand-written physics, which is why it does not go through a reader.
- `catalog.py` reads the sample configs and answers which samples a command means.
    - The `Sample` class is a dict subclass giving attribute access, `sample.name`.
    - `select` backs the five sample flags on every command that takes them, and they do not behave alike. `--family`, `--era` and `--tag` resolve case-insensitively against what exists and raise on a value matching nothing, naming every value that does exist; two spellings differing only in case are ambiguous and also raise. `--name` is exact and case-sensitive. `--match` is a plain glob with no check at all, so a pattern matching nothing leaves the selection empty and the command exits with "No samples matched the selection".
- `content.py` resolves a content preset into what a job receives.
    - `KIND_TO_PLUGIN` is the point of the module: a physics-facing `type` maps onto the CMSSW plugin that builds that table, so nobody writing a config has to know a plugin name. A new kind of collection is an entry here, plus any of the sets below it whose behavior it shares.
- `selections.py` resolves a selection config into something the engine can run without further lookups.
    - It resolves for exactly one era. Thresholds, trigger lists and flag lists may each be written as a plain value or as an object keyed by era, and `_resolveThreshold` collapses them. Passing `era=None` is legal only for a config that uses none of that, and everything else raises rather than guessing a year.
    - Trigger names are expanded into path lists here via `loadTriggerPaths`, so the resolved selection is self-contained and a worker never reads `config/triggers/`. That is what lets `batch.py` ship a single JSON to the grid.
    - The `*_FIELDS` sets exist to reject a misspelled key. A typo in a cut would otherwise be silently ignored and the cut would quietly do less.
    - `CUT_TYPES` and the engine's `_cutMask` must be kept in step; a type accepted here and unknown there fails only when the selection runs.
    - It validates every `quantity` against `select.quantities.QUANTITIES`, which is why this module imports from `select/`. The direction is deliberate: the vocabulary belongs to the code that evaluates it, and `quantities.py` imports nothing from kamui, so there is no cycle.
    - An `anyOf` alternative that does not apply to the era is dropped at resolve time. Leaving it in would have it fail later on trigger paths that never existed that year.
    - `orderedMinPt` is checked to be descending, because it is matched against pT-sorted objects and an ascending ladder would pass everything.
- `sites.py` reads `sites.json`, expanding environment variables as it goes.
    - Expansion happens at config-load time on the submitting machine, deliberately. On a worker node `$USER` is the batch account, and output would go somewhere wrong.
    - An unset variable raises, since a path with a literal dollar sign in it fails much later and less clearly.


## Talking to the Grid - grid/
- `das.py` caches every answer on disk under `.dasCache/`, keyed by (instance, query, jsonOut). 
  - DAS is slow and its answers rarely change. `--refresh` bypasses it.
   - `CACHE_MAX_AGE_DAYS` is the definition of stale, shared by `query`, `cacheStats` and `pruneCache`.
    - An entry past the limit is skipped on read but never removed, so the cache grows until something prunes it.
    - `pruneCache` can be used to remove stale entries
- DAS answers a dataset name it does not know with a full summary record of zeros and null dates. 
  - `datasetSummary` therefore decides a dataset exists from `max_ldate`
- Need a valid proxy!
## Submitting Jobs - submit/
- `prepare` writes the job area, `submit` only shells out. `--dryRun` runs the first and skips the second, so the files it leaves are the ones a real submission would use.
- Re-using a task name prompts before overwriting, because the old area is the only local record of a submission that may still be running. Declining writes to `<task>_n`, and `prepare` returns the name it actually used, so the caller and the EOS output directory follow it. A non-interactive run never overwrites.
- `--filesPerJob` is `default=None` so an explicitly passed value can be told from an absent one, letting the flag beat a sample's `unitsPerJob` while the sample value still beats the built-in.
- `task.json` is what makes a production reproducible.
    - It embeds the resolved content, so it stays readable when the preset changes.
    - A dirty tree means the commit alone does not describe the task, so check that flag first when ntuples disagree with expectations.
    - `publishRecord` copies it to the EOS output directory on real submission, never on `--dryRun`. Job areas are gitignored scratch, so the EOS copy is the only one that lives as long as the ntuples.
    - A failed publish warns and returns False.
    - Anything added to a submission path that changes what a job does belongs in it.
- The content preset is flattened into the job area and shipped with the job.
- `crab.py`
    - `requestName` is capped at 100 characters by CRAB, so `_requestName` truncates. `_checkRequestNames` rejects a submission whose samples would collide after truncation, before the job area is touched.
    - `submit` returns `(ok, bad)` and keeps going, so one bad sample cannot strand the rest of a production.
- `condor.py`
    - `resubmit` decides what failed by looking at EOS, not at condor: a job whose output is present is done however it exited. It refuses while any of this task's jobs are still queued, since retrying a running job writes the same output twice.
    - A sample whose file list came back empty gets no jobs. It is named in a warning and recorded in `droppedSamples`, since a silently shorter production looks like a successful one.
    - Each job builds a CMSSW area with `scramv1 project` before running, so there is fixed startup cost per job. Jobs over very few files spend most of their wall time on it.
    - A task can mix content presets and data with MC, so a run script is written per `(preset, isMC)` combination and each row of `jobList.txt` names the script it needs. The JDL's executable is `$(script)`.
    - `+DesiredOS = "EL9"` is the LPC worker OS selector. If jobs sit idle indefinitely, `+REQUIRED_OS = "rhel9"` is the alternative.
    - Output is copied back with `xrdcp` from inside the job because EOS is not a condor-visible filesystem.


## Selecting Events - select/
- The stage is pure Python over the ntuples: uproot and awkward, no CMSSW. That is what makes the local backend viable and why a selection can be iterated on in seconds.
- Nothing here reads a config directory. The selection arrives already resolved, from `configReaders/selections.py` on the submitting machine.
- `engine.py`
    - `applySelection` accumulates one boolean mask and never drops rows until the end, so every cut's efficiency is measured against the same array and the cutflow is exact.
    - The output has the same branches as the input. This stage removes events, never objects: an `object` cut is an existence test over a collection, and the objects that failed it stay in the file.
    - `_readAll` concatenates every input file into one in-memory array. That sets the real limit on `--filesPerJob`, and it is why a large pass has to go through condor rather than a bigger local run.
    - `_localCopy` copies a `root://` path to scratch before opening it. uproot needs `fsspec-xrootd` to read xrootd directly and the CMSSW python stack does not ship it. `normalization.py` imports this function for the same reason.
    - `_write` groups a collection's fields into one `ak.zip` record so uproot emits one counter per collection. Writing each jagged branch separately makes uproot invent `nElectron_pt`, `nElectron_eta` and so on, and the schema then drifts with every selection pass.
    - `_primaryVertex` takes the first vertex passing `PV_isGood`, not index 0. The ntuples keep every reconstructed vertex and a low-ndof fit sits at index 0 often enough to move dz by a centimetre.
    - `_trackIP` recomputes dz and dxy from the stored track reference point, including the beam tilt, because the ntuple stores the ingredients rather than a finished impact parameter.
    - A trigger pattern matching no branch contributes nothing and is not an error. The note records how many of the requested paths were present, which is where a wrong era or a missing skim shows up.
    - Cut kinds carrying `invert` are how an orthogonality veto is written: state the other channel's selection, then invert it, so the two channels cannot drift apart.
- `quantities.py`
    - `QUANTITIES` is the entire vocabulary a selection config may name. Adding a quantity is an entry here; nothing else changes.
    - `tightLepVeto` demands an era and raises for anything outside Run 2. Guessing a working point would bias a whole year's yields silently, and the Run 3 table is not written down yet.
    - The 2017/18 TightLepVeto is a flat conjunction with no barrel/endcap split, which is not the published working point. It matches JMTucker's `jet_cuts_2017p8`, and reinstating the split admits jets between |eta| 2.4 and 2.5 and moves HT and every jet ladder. The 2016 definition does carry the split, because JMTucker's does.
    - `caloHT30` sums raw pT with no identification and no energy correction, since that is the quantity the displaced-dijet triggers actually cut on.
- `io.py`
    - `_namesSample` tests the sample name as a whole path component. A substring test would make `..._2016` claim `..._2016APV`'s files, which is a real pair in the catalog.
    - `findInputs` walks the whole task directory and keeps what names the sample, so it handles both layouts: condor writes `<task>/<sample>/`, CRAB nests under `<task>/<primaryDataset>/<sample>/<timestamp>/0000/`.
    - It returns an empty list on any xrdfs failure. A missing task and an unreachable EOS look the same to the caller.
    - `writeCutflow` writes to a temporary file and renames, so an interrupted run leaves the previous cutflow intact.
- `batch.py`
    - Has its own `taskDir`, under `ntupleSelection/jobs/`, distinct from `submit/common.taskDir`. The two stages must not share a task namespace.
    - `packageKamui` tars the package into the job area, so a worker imports kamui with no checkout and no CMSSW integration. `__pycache__` is filtered out, since a stale `.pyc` from a different Python would ship with it.
    - One resolved selection JSON is written per era and named in `jobList.txt` through the run script, the same mechanism `submit/condor.py` uses for `(preset, isMC)`.
    - The memory and disk requests are function arguments with no CLI flag. Add flags when a pass actually needs them.
- `runOne.py` writes the cutflow next to the output as `<output>.cutflow.json`, and the run script copies both to EOS. Merging those per-job cutflows is not implemented, which is why `kamui cutflow` only works after a local pass.
- `normalization.py`
    - Anything normalizing must call `denominator`, which returns `None` for a sample that has no recorded sum, rather than reading `sumGenWeight` out of the file and getting a `KeyError`.
    - `record` merges into the existing entry, so the DAS count recorded when a sample was added survives a later weight-sum measurement.
    - Files missing a `Runs` tree are skipped rather than counted as zero.


## Extras - helpers/
- `banner.py` writes to stderr, not stdout, so it can never contaminate piped output.
- It draws only when stderr is a terminal, keeping scripts, cron and log files clean.
- The braille art is wrapped in a `try` for `UnicodeEncodeError`, so a terminal that cannot encode it gets no banner. This matters on LPC, where non-UTF-8 environments turn up.
- The banner is drawn only for help output: `main()` scans raw `argv` before `parse_args` and draws when the arguments are empty or carry `-h`/`--help`. Real work never prints it. `--noBanner` is registered so `--help` documents it and is read from raw argv, so `args.noBanner` is never used. It sits on the top-level parser and has to precede the command.
