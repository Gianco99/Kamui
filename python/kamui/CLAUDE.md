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
    - The only command that accepts an empty selection, via `pick(args, required=False)`. Every other command exits when nothing matches: listing nothing is a valid answer.
    - The table uses fixed column widths, and `dvRun2Displaced` is 15 characters in a 10-wide column, so tags run ragged.
- The nine `cmdX` docstrings are not just documentation: `main()` passes them to argparse as `description=`, so they are the per-command `--help` text.


## The Basics - foundations/
- Nothing here may import from anywhere else in kamui.
- `paths.py` is the only module allowed to know the repository layout. Anything else that hardcodes a directory name is a bug, and moving a directory should mean editing this file alone.
    - It derives the repository root from its own file location, which is why the package can be moved without configuration. That also means it breaks silently if the file is relocated without updating the `dirname` chain.
    - `SAMPLES_DIR_STAGE` and `SAMPLES_DIR` are confusingly close: the first is `SamplesFromDAS/`, the second is `config/samples/` inside it.
- `config.py` merges layer by layer, and a list replaces the list below rather than appending.
    - For example: `dvRun2Lepton` is built on `dvRun2Displaced` and swaps its 11 displacement HLT paths for 8 lepton ones.
    - The cost falls on two keys where adding is the natural intent: `miniaod.keep`, restated in full by `dvBase`, `dvSignal` and `dvFull`, and `tags`, restated by all three grids in `run2Validation`. If that becomes annoying, add an opt-in append marker to `deepMerge` rather than changing the default.


## Reading the Configs - configReaders/
- Nothing outside this folder may open a config file.
    - `./kamui check` enforces it by scanning for `paths.*_DIR` and `paths.SITES_FILE` outside `configReaders/`.
    - This is why `loadSites` lives here rather than in `submit/`, and why `cmdCheck` calls `validateTriggers()` instead of reading the trigger directory itself.
- A leading underscore marks a function as internal to its module.
- `catalog.py` reads the sample configs and answers which samples a command means.
    - The `Sample` class is a dict subclass giving attribute access, `sample.name`.


## Extras - helpers/
- `banner.py` writes to stderr, not stdout, so it can never contaminate piped output.
- It draws only when stderr is a terminal, keeping scripts, cron and log files clean.
- The braille art is wrapped in a `try` for `UnicodeEncodeError`: a terminal that cannot encode it gets no banner rather than a crash. This matters on LPC, where non-UTF-8 environments turn up.
- `--no-banner` is handled twice on purpose. `main()` scans raw `argv` before `parse_args`, because the banner has to print before argument parsing to appear on `--help` and on errors. The registered flag exists only so `--help` documents it and argparse does not reject it, which is why `args.noBanner` is never read.
