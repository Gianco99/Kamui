# Foundations

The bottom layer everything else is built on.

`paths.py`: Knows the paths where everything lives. It works this out from its own location, so there is nothing to set up and the framework runs wherever you check it out.

`config.py`: Reads the JSON config files, dropping `_` comment keys and flattening `include` chains. See `config/README.md` for how includes merge.

## Caveats

- Nothing here may import from anywhere else in kamui.
- `paths.py` is the only module allowed to know the repository layout.
  - Anything else that hardcodes a directory name is considered a bug.
  - Moving a directory should mean editing this file alone.
