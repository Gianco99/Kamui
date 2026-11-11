# The files-per-job and memory defaults are defined in several places.

- **Where:** `python/kamui/submit/condor.py:20` and `85`, `python/kamui/submit/crab.py:16` and `74`, `python/kamui/select/batch.py:22` and `24`, and `python/kamui/cli.py:689`.
- **Problem:** Changing a default takes the same edit in several files, and a missed one leaves the backends disagreeing.
- **Fix:** Define them once in `python/kamui/submit/common.py`.
