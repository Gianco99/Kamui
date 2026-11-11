# A production record with no `maxFiles` key counts as a read of the whole dataset.

- **Where:** `python/kamui/select/io.py:190` reads a missing key as no cap.
- **Problem:** A pass over such a task gets a generated row for the whole dataset, out of scale with the files the task read. The local tasks `testShipPlugins_condor`, `run2Val` and `tutorial` have such records.
- **Fix:** Treat a record without the key as partial, or add the key to those records.
