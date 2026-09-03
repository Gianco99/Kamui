# foundations/

- Nothing here may import from anywhere else in kamui.
- `paths.py` is the only module allowed to know the repository layout.
  - Anything else that hardcodes a directory name is considered a bug
  - Moving a directory should mean editing this file alone.
- `config.py` merges layer by layer, and a list replaces the list below.
