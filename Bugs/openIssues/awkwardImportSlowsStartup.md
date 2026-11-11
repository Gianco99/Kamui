# Every `kamui` command takes about 1 to 2 s to start, almost all of it importing awkward.

- **Where:** `python/kamui/cli.py:25` imports `select`, whose `io.py:21` imports `engine.py`, which imports awkward at line 17.
- **Problem:** Commands that never read an ntuple, such as `list` or `check`, still wait for the import.
- **Fix:** Import awkward lazily inside `select/`.
