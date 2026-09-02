# grid/

- `das.py` caches every answer on disk under `.dasCache/`, keyed by (instance, query, jsonOut). 
  - DAS is slow and its answers rarely change. `--refresh` bypasses it.
   - `CACHE_MAX_AGE_DAYS` is the definition of stale, shared by `query`, `cacheStats` and `pruneCache`.
    - An entry past the limit is skipped on read but never removed, so the cache grows until something prunes it.
    - `pruneCache` can be used to remove stale entries
- DAS answers a dataset name it does not know with a full summary record of zeros and null dates. 
  - `datasetSummary` therefore decides a dataset exists from `max_ldate`
- Need a valid proxy!
