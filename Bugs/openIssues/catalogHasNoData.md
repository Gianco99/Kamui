# The catalog has no data samples, so the blind guard has only been tested with a stubbed sample.

- **Where:** `python/kamui/select/io.py:174-176` (`preparePass`) refuses a blind selection on data. No sample file in `config/samples/` sets `isMC` to false.
- **Problem:** The guard that keeps signal-region selections off data has never run on a real data sample.
- **Fix:** Once data samples are registered, check that `select` refuses a blind selection on one.
