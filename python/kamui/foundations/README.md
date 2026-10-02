# Foundations

The bottom layer everything else is built on: where each file lives, and how a JSON config file is read.

`paths.py`: Knows the paths where everything lives. It works this out from its own location, so there is nothing to set up and the framework runs wherever you check it out.

`config.py`: Reads the JSON config files and drops the comment keys, the ones starting with `_`. A file can pull in other files with `include`, and those files can do the same. The file's own content overrides what it pulls in. Objects merge key by key at every depth, and a list or single value replaces the included one whole.

## Caveats

- Nothing here may import from anywhere else in kamui.
- `paths.py` is the only module allowed to know the repository layout.
  - Anything else that hardcodes a directory name is considered a bug.
  - Moving a directory should mean editing this file alone.
