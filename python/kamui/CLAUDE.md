# Kamui

## Design Premise
- Kamui is the CLI for the whole analysis framework.
- Sample processing, turning CMS datasets to ntuples on EOS, is the only stage implemented so far.
- When a new stage is added it belongs here as commands, not as a separate script alongside kamui.

The design principle the whole package serves is that the physics lives in configuration files and this code only executes what they say. When reviewing or extending anything here, that is the constraint to protect.


## Main Driver - cli.py
- Every command lives in this one file. Adding one is two edits here: a `cmdX` handler, and a `sub.add_parser` block that points at it.
- Keep it thin. It parses, calls a module, and prints. The actual behavior belongs in the modules so they can be imported without the CLI.
- `list`
    - The only command that accepts an empty selection, via `_pick(args, required=False)`. Every other command exits when nothing matches: listing nothing is a valid answer.
- `content`
    - `--write` emits exactly the JSON a job is handed, and `submit` calls the same resolver.
    - `--data` changes the answer, so a preset has to work both ways. `check` resolves every preset twice for that reason.
- `find`
    - The one command that ignores the catalog entirely. Everything else answers questions about samples we already wrote down; this asks DAS what exists. Private datasets need `--instance prod/phys03`, and forgetting that returns nothing.
- `stage`
    - Copies whole MiniAOD files to EOS, which is expensive and rarely what you want. It exists for inspecting a file and for prototyping a content preset against something local. Production goes through `submit`, which streams from the grid and never copies the input.
    - Copies the whole dataset unless `--maxFiles` caps it, which on a large dataset is hundreds of GB.
- `query`
    - The only command that can tell you a dataset is real.
- `submit`
    - CRAB takes the dataset name and splits it itself; condor needs a resolved file list, so only the condor path queries DAS.
- `status`
    - Summarizes `task.json`. The record runs to tens of kB, so printing it whole buries the few lines anyone wants.
    - Reads the backend out of the record, so a task is always queried the way it was submitted.
    - Condor jobs are filtered by the cluster id recorded at submit time. Without one it lists the whole queue and says so, which otherwise reads as if it were this task.
- `cache`
    - `--prune` drops only expired entries, `--clear` drops everything. Clearing costs a full refetch from a slow service.
- `check`
    - Everything it does must work with no proxy.
    - It enforces the two architectural boundaries by reading source: `foundations/` importing from above, and anything outside `configReaders/` touching a config path. Both are greppable, which is what makes them checkable.
    - It resolves every preset for both MC and data, including unreferenced ones, which break just as loudly.
    - Returns 1 on any problem so it can gate CI or a submission script.
- `main()` passes the nine `cmdX` docstrings to argparse as `description=`, so they are the per-command `--help` text.


## The Basics - foundations/
- Nothing here may import from anywhere else in kamui.
- `paths.py` is the only module allowed to know the repository layout. Anything else that hardcodes a directory name is a bug, and moving a directory should mean editing this file alone.
    - It derives the repository root from its own file location, which is why the package can be moved without configuration. That also means it breaks silently if the file is relocated without updating the `dirname` chain.
- `config.py` merges layer by layer, and a list replaces the list below.
    - For example: `dvRun2Lepton` is built on `dvRun2Displaced` and swaps its 11 displacement HLT paths for 8 lepton ones.
    - The cost falls on two keys where adding is the natural intent: `miniaod.keep`, restated in full by `dvBase`, `dvSignal` and `dvFull`, and `tags`, restated by all three grids in `run2Validation`. If that becomes annoying, add an opt-in append marker to `deepMerge`.


## Reading the Configs - configReaders/
- Nothing outside this folder may open a config file.
    - `./kamui check` enforces it by scanning for `paths.*_DIR` and `paths.SITES_FILE` outside `configReaders/`.
    - This is why `loadSites` lives here, and why `cmdCheck` calls `validateTriggers()` to reach the trigger directory.
- `catalog.py` reads the sample configs and answers which samples a command means.
    - The `Sample` class is a dict subclass giving attribute access, `sample.name`.
- `content.py` resolves a content preset into what a job receives.
    - `KIND_TO_PLUGIN` is the point of the module: a physics-facing `type` maps onto the CMSSW plugin that builds that table, so nobody writing a config has to know a plugin name. A new kind of collection is an entry here, plus any of the sets below it whose behavior it shares.
- `sites.py` reads `sites.json`, expanding environment variables as it goes.
    - Expansion happens at config-load time on the submitting machine, deliberately. On a worker node `$USER` is the batch account, and output would go somewhere wrong.
    - An unset variable raises, since a path with a literal dollar sign in it fails much later and less clearly.
- `slimming.py` maps a preset's `miniaod` group names onto EDM outputCommands.
    - Keeps are written label-first, because a class name spelled slightly wrong keeps nothing and reports nothing.
    - A group naming a collection that does not exist in a given campaign is harmless: the keep matches nothing.


## Talking to the Grid - grid/
- `das.py` caches every answer on disk under `.dasCache/`, keyed by (instance, query, jsonOut). DAS is slow and its answers rarely change. `--refresh` bypasses it.
    - `CACHE_MAX_AGE_DAYS` is the single definition of stale, shared by `query`, `cacheStats` and `pruneCache`. Reading and pruning have to agree on it or prune deletes entries still in use.
    - An entry past the limit is skipped on read but never removed, so the cache grows until something prunes it.
    - `pruneCache` removes what `query` refuses: expired, unparseable, or result-less entries, aged by file mtime, the same clock `query` reads.
    - Cache layout is known only to `das.py`; anything counting or measuring entries calls `cacheStats`.
- It refuses to run without a valid proxy.
- `fetch.py` copies whole files and skips anything already on EOS. Nothing in the production path uses it: `submit` streams from the grid instead.

## Submitting Jobs - submit/
- `prepare` writes the job area, `submit` only shells out. `--dry-run` runs the first and skips the second, so the files it leaves are the ones a real submission would use.
- Re-using a task name prompts before overwriting, because the old area is the only local record of a submission that may still be running. Declining writes to `<task>_n`, and `prepare` returns the name it actually used, so the caller and the EOS output directory follow it. A non-interactive run never overwrites.
- `--filesPerJob` is `default=None` so an explicitly passed value can be told from an absent one, letting the flag beat a sample's `unitsPerJob` while the sample value still beats the built-in.
- `task.json` is what makes a production reproducible.
    - It embeds the resolved content, so it stays readable when the preset changes.
    - A dirty tree means the commit alone does not describe the task, so check that flag first when ntuples disagree with expectations.
    - `publishRecord` copies it to the EOS output directory on real submission, never on `--dry-run`. Job areas are gitignored scratch, so the EOS copy is the only one that lives as long as the ntuples.
    - A failed publish warns and returns False.
    - Anything added to a submission path that changes what a job does belongs in it.
- The content preset is flattened into the job area and shipped with the job.
- `crab.py`
    - `requestName` is capped at 100 characters by CRAB, so `_requestName` truncates. `_checkRequestNames` rejects a submission whose samples would collide after truncation, before the job area is touched.
    - `submit` returns `(ok, bad)` and keeps going, so one bad sample cannot strand the rest of a production.
    - Whether CRAB accepts two EDM output modules at once, which is what `--output both` asks for, is unverified.
- `condor.py`
    - A sample whose file list came back empty gets no jobs. It is named in a warning and recorded in `droppedSamples`, since a silently shorter production looks like a successful one.
    - Each job builds a CMSSW area with `scramv1 project` before running, so there is fixed startup cost per job. Jobs over very few files spend most of their wall time on it.
    - A task can mix content presets and data with MC, so a run script is written per `(preset, isMC)` combination and each row of `jobList.txt` names the script it needs. The JDL's executable is `$(script)`.
    - `+DesiredOS = "EL9"` is the LPC worker OS selector. If jobs sit idle indefinitely, `+REQUIRED_OS = "rhel9"` is the alternative.
    - Output is copied back with `xrdcp` from inside the job because EOS is not a condor-visible filesystem.

## Extras - helpers/
- `banner.py` writes to stderr, not stdout, so it can never contaminate piped output.
- It draws only when stderr is a terminal, keeping scripts, cron and log files clean.
- The braille art is wrapped in a `try` for `UnicodeEncodeError`, so a terminal that cannot encode it gets no banner. This matters on LPC, where non-UTF-8 environments turn up.
- `--no-banner` is handled twice on purpose. `main()` scans raw `argv` before `parse_args`, because the banner has to print before argument parsing to appear on `--help` and on errors. The registered flag exists only so `--help` documents it, which is why `args.noBanner` is never read. It sits on the top-level parser, so it has to precede the command.
