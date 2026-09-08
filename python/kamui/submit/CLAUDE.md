# Submit

- Re-using a task name prompts, and declining writes to `<task>_n`, which the EOS output directory then follows. A task that recorded a condor cluster or holds a CRAB work area refuses outright whatever the answer, and `--overwrite` skips the prompt in a script as readily as at a terminal.
- A content preset resolves against its era set, so `dvBase` for a Run 2 era and for a Run 3 one are different bodies. The resolved JSON, the run script and the `jobList.txt` rows are all keyed on `(preset, isMC, eraGroup)`.
- `task.json` embeds the resolved content, and `publishRecord` copies it to EOS on real submission only. A retry updates the local copy alone, and job areas are gitignored scratch, so the EOS copy is the only one that lasts as long as the ntuples.
- `crab.py`
    - CRAB caps `requestName` at 100 characters, so `_requestName` truncates and `_checkRequestNames` rejects samples that would collide after truncation.
    - CRAB ships the release it is submitted from, so `task.json` records the environment's `CMSSW_VERSION`. `--maxFiles` and `--refresh` do nothing here.
- `condor.py`
    - `resubmit` reads EOS to decide what failed, matching by filename, so a job whose output is present is done however it exited. The queued-job guard lives in `_cmdResubmit`, and `--forceResubmit` skips it.
    - The retry JDL is built by string replacement against the `JDL` template, so reformatting its alignment breaks `resubmit`.
