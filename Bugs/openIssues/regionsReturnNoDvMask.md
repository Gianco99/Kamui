# A region selection gives no way to tell which DVs passed it.

- **Where:** `python/kamui/select/engine.py:363-389` (`applySelection`) returns the cutflow and writes the passing events. The per-DV mask is built in `_objectMask` (218-228) and only summed per event in `_quantity` (284-296).
- **Problem:** The template pool needs the DV that makes an event 1V, and the observed DV pairs.
- **Fix:** Export a per-DV mask from `select/engine.py`, and add a helper that orders a region's DVs as JMTucker does.
