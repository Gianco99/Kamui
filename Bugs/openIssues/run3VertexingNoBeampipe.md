# The Run 3 `vertexing.json` has no `beampipe` block, so Run 3 DV content does not resolve.

- **Where:** `config/content/run3/collections/vertexing.json:42-52`, the `vertexing` block of the `DV` collection. `python/kamui/configReaders/content.py:379-381` refuses it, and `check` skips the file through `PARKED_CONTENT` (`python/kamui/cli.py:58`).
- **Problem:** No Run 3 preset can write DVs, and there is no source for the Run 3 beampipe numbers yet.
- **Fix:** Add the block once a source exists, then remove the `run3` entry from `PARKED_CONTENT`.
