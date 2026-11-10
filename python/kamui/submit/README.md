# Submit

Everything that turns a set of samples into running jobs, behind the `submit`, `status` and `resubmit` commands. One run of `submit` is a task, named with `--task`. Kamui writes the task's files into its job area, `ntupleProduction/jobs/<task>/`, then sends the jobs to a backend, the system that runs them.

- The backends are condor, which runs the jobs on the LPC cluster, and CRAB, which runs them at grid sites.
- The resolved content is a sample's content preset written out in full, as its job receives it, so a job never reads `config/`.

`common.py`: The code both backends share. It picks the task's job area, checks that the task's EOS output directory is empty, and writes the resolved content and `task.json`. It also holds `chunk`, which splits input files into condor jobs.

`condor.py`: The condor backend.

`crab.py`: The CRAB backend.

See `ntupleProduction/README.md` for choosing a backend, what a job area holds and where the output lands.

## Caveats

- A task name belongs to one production. `submit` reuses a job area that was never submitted, such as one a dry run left, and refuses a task whose area shows a submission or whose EOS output directory already holds files.
- One task can mix eras, presets, and MC with data. Each combination of preset, era, and MC or data gets its own resolved content file. On condor it also gets its own run script, and each row of `jobList.txt` names the script its job runs.
- Jobs run the plugins compiled in the CMSSW area you submit from, such as the DV vertexer. Condor ships them in `cmsswArea.tar.gz` and CRAB in its sandbox. So after changing a plugin, run `scram b` before submitting: kamui refuses to submit when a source file under that area's `src/` is newer than its compiled libraries. For condor that area must also be the release in `config/sites.json`, since that is the one the workers build.
- Jobs run the copies of `ntuple_cfg.py` and `ntupleTables.py` that `submit` puts in the job area, so editing those files or switching branches leaves a submitted task and its retries alone. To try a change to them, submit a new task.
- `task.json` is the full record of what a task ran, content included. Kamui copies it to EOS next to the ntuples when the task is submitted. Keep that copy, since the local job area is scratch. A condor retry updates only the local copy. `select` reads the local copy to find a task's ntuples, so without it, pass `--inputBase`.
- `crab.py`
    - CRAB limits request names to 100 characters, so kamui shortens long ones, and stops you if two samples would end up with the same shortened name.
    - CRAB uses the CMSSW release you submit from, and `task.json` notes which one. `--maxFiles` caps the input files of each sample, and `--refresh` does nothing for CRAB.
    - A sample whose `crab submit` failed has no CRAB project, so kamui lists it in `task.json`. `status` names it and `resubmit` submits it again. If the failed submit left a project under `crab/`, check it with `crab status -d` and delete it before `resubmit`, since `crab submit` refuses a project that already exists.
    - CRAB packs the compiled plugins at each `crab submit`, so a sample that `resubmit` submits again runs whatever your CMSSW area has built at that moment.
- `condor.py`
    - `resubmit` treats a job as done once its output is on EOS, even if the job reported an error. It refuses a task that was never submitted. It asks each schedd the task and its retries went to, and refuses while any job is idle, running or held, or while a schedd does not answer, unless you pass `--forceResubmit`. A held job never finishes by itself, so `status` and `resubmit` print the `condor_rm` command that clears it.
    - `resubmit` builds its retry file by editing the text of the `JDL` template, so reformatting that template breaks it.
