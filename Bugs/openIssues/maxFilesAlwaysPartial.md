# A production `--maxFiles` at least as large as the dataset still marks the inputs as partial.

- **Where:** `python/kamui/select/io.py:190` marks every record with a `maxFiles` value as partial. CRAB records only the flag (`python/kamui/submit/crab.py:118` and `131`).
- **Problem:** The cutflow leaves out its generated row (`withGenerated`, `io.py:260-275`) even when the jobs read the whole dataset.
- **Fix:** Mark a sample partial only when the cap is below the dataset's file count, taken from DAS at submit.
