# foundations/

- Nothing here may import from anywhere else in kamui.
- `paths.py` is the only module allowed to know the repository layout. Anything else that hardcodes a directory name is a bug, and moving a directory should mean editing this file alone.
    - It derives the repository root from its own file location, which is why the package can be moved without configuration. That also means it breaks silently if the file is relocated without updating the `dirname` chain.
- `config.py` merges layer by layer, and a list replaces the list below.
    - For example: `dvLepton` and `dvDisplaced` are both `dvFull` plus a skim, differing only in which trigger config they name.
    - The cost falls on two keys where adding is the natural intent: `miniaod.keep`, restated in full by `dvBase`, `dvSignal` and `dvFull`, and `tags`, restated by all three grids in `run2Validation`. If that becomes annoying, add an opt-in append marker to `deepMerge`.
