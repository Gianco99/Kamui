# The cutflow's "Applied as" text spells out `tightDV` in full for every count condition.

- **Where:** `python/kamui/select/engine.py:299-318` (`_quantityText`, `_bounds`) builds the note from the resolved requirements, where the definition is already expanded. `python/kamui/select/io.py:367-368` prints it.
- **Problem:** A region's row reads `number of DV with insideBeampipe >= 1, dBV >= ..., dBVErr < ..., mass >= ..., sumPt >= ..., nTracks >= 3 and nTracks <= 3 >= 2`, which buries the count.
- **Fix:** Name the definition once and write a count as "exactly 1" or "at least 1". This needs the resolved selection to keep the definition's name.
