# Grid

- A grid proxy with more than an hour left is needed for any DAS call that misses the cache, and the check happens after the cache read.
- `das.py`
    - Answers are cached under `ntupleProduction/.dasCache/`, stale after `CACHE_MAX_AGE_DAYS`.
    - An empty answer that arrived with a dasgoclient warning is returned without being cached.
    - DAS answers a name it does not know with a summary of zeros and null dates, so `datasetSummary` decides a dataset exists from `max_ldate` or a non-zero `nfiles`.
    - `nanoSibling` sorts its matches as plain strings, which puts `NanoAODv9` above `NanoAODv12`. See the README.
- `fetch.py`
    - A file already on EOS is matched by name alone, so a truncated file left by an interrupted copy is skipped forever.
    - The first number `stage` returns counts files present: a skip and a dry run both increment it.
    - `xrdcp` runs with no timeout.
