# Submit

Everything that turns a set of samples into running jobs, behind the `submit`, `status` and `resubmit` commands. One run of `submit` is a task, named with `--task`. Kamui writes the task's files into its job area, `ntupleProduction/jobs/<task>/`, then sends the jobs to a backend, the system that runs them.

- The backends are condor, which runs the jobs on the LPC cluster, and CRAB, which runs them at grid sites.
- The resolved content is a sample's content preset written out in full, as its job receives it, so a job never reads `config/`.

`common.py`: The code both backends share. It picks the task's job area and writes the resolved content and `task.json`. It also holds `chunk`, which splits input files into condor jobs.

`condor.py`: The condor backend.

`crab.py`: The CRAB backend.

See `ntupleProduction/README.md` for choosing a backend, what a job area holds and where the output lands.

## Caveats

- If you reuse a task name, kamui asks before overwriting the old one. Say no, or run from a script, and it saves the new task as `<task>_2`, and so on. `--overwrite` skips the question. It never overwrites a task that already sent jobs to condor or CRAB, so give those a new name.
- One task can mix eras, presets, and MC with data. Each combination of preset, era, and MC or data gets its own resolved content file. On condor it also gets its own run script, and each row of `jobList.txt` names the script its job runs.
- `task.json` is the full record of what a task ran, content included. Kamui copies it to EOS next to the ntuples when the task is submitted. Keep that copy, since the local job area is scratch. A condor retry updates only the local copy.
- `crab.py`
    - CRAB limits request names to 100 characters, so kamui shortens long ones, and stops you if two samples would end up with the same shortened name.
    - CRAB uses the CMSSW release you submit from, and `task.json` notes which one. `--maxFiles` and `--refresh` do nothing for CRAB.
- `condor.py`
    - `resubmit` treats a job as done once its output is on EOS, even if the job reported an error. It refuses to resubmit while any of the task's jobs are still queued, unless you pass `--forceResubmit`.
    - `resubmit` builds its retry file by editing the text of the `JDL` template, so reformatting that template breaks it.
