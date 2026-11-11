# Foundations

This folder is the bottom layer everything else is built on: it knows where each file lives, and how a JSON config file is read.

`paths.py`: Knows the paths where everything lives. It works them out from its own location, so there is nothing to set up and the framework runs wherever you check it out.

`config.py`: Reads the JSON config files and drops the comment keys, the ones starting with `_`. A file can pull in other files by listing their names under `include`, and those files can do the same. The file's own content overrides what it pulls in. Objects merge key by key at every depth, and a list or single value replaces the included one whole. For example, if a file holding `{"a": {"y": 3}, "b": [4]}` includes one holding `{"a": {"x": 1, "y": 2}, "b": [1, 2]}`, the result is `{"a": {"x": 1, "y": 3}, "b": [4]}`.

## Caveats

- Nothing here may import from anywhere else in the `kamui` package.
- `paths.py` is the only module allowed to know the repository layout.
  - Any other code that hardcodes a directory name is a bug.
  - Moving a directory should mean editing `paths.py` alone.
