# `check` never compares the names in a selection with the content, so a misspelled name is caught only at select time.

- **Where:** `python/kamui/cli.py:505-515`, the Selections step of `check`, which only resolves each selection.
- **Problem:** A misspelled collection, variable, quantity, flag or trigger in a selection passes `check`.
- **Fix:** Add a static name check to `check`. `collectionsUsed()` (`python/kamui/select/engine.py:333-350`) and `DERIVED_VARIABLES` (173-176) can serve it.
