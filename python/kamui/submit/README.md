# Submit

Everything that turns a set of samples into running jobs.

`common.py`: The task directory, what each job should write, the input files split into jobs, and `task.json`, which both backends share.

`condor.py`: The condor backend.

`crab.py`: The CRAB backend.

See `ntupleProduction/README.md` for choosing a backend, what a job area holds and where the output lands.

## Caveats

- If you reuse a task name, kamui asks before overwriting the old one. Say no, or run from a script, and it saves the new task as `<task>_2`, and so on. `--overwrite` skips the question. It never overwrites a task that already sent jobs to condor or CRAB, so give those a new name.
- One task can hold several eras. Each preset, MC or data, and era gets its own resolved content, run script and rows in `jobList.txt`.
- `task.json` is the full record of what a task ran, content included. Keep the copy on EOS: it stays with the ntuples, while the local job area is scratch and a retry only updates the local copy.
- `crab.py`
    - CRAB limits request names to 100 characters, so kamui shortens long ones, and stops you if two samples would end up with the same shortened name.
    - CRAB uses the CMSSW release you submit from, and `task.json` notes which one. `--maxFiles` and `--refresh` do nothing for CRAB.
- `condor.py`
    - `resubmit` treats a job as done once its output is on EOS, even if the job reported an error. It waits while any of the task's jobs are still queued, unless you pass `--forceResubmit`.
    - `resubmit` builds its retry file by editing the text of the `JDL` template, so reformatting that template breaks it.
