# Inside an `anyOf` cut, a trigger path missing from the ntuple counts as not fired, so a misspelled path in an inverted alternative keeps events without a warning.

- **Where:** `python/kamui/select/engine.py:128-132` (`_anyOfCut`). The cut stops the pass only when every alternative misses a path (137-138), while a top-level trigger cut that matches no path stops it at 94-95.
- **Problem:** The rule exists because part of an era can run without a path. An inverted trigger cut whose path is misspelled passes every event.
- **Decision needed:** Confirm this is the wanted behavior.
