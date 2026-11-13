# Submit

This folder holds the code behind the `submit`, `status` and `resubmit` commands, which turn a set of samples into running jobs. One run of `submit` is a task, named with `--task`. Kamui writes the task's files into its job area, `ntupleProduction/jobs/<task>/`, then sends the jobs to a backend, the system that runs them. For example, `./kamui submit --tag <tag> --task <task>` builds `ntupleProduction/jobs/<task>/` and sends its jobs to condor, the default backend.

- The backends are condor, which runs the jobs on the LPC cluster, and CRAB, which runs them at grid sites.
- The resolved content is a sample's content preset written out in full, as its job receives it, so a job never reads `config/`.

`common.py`: The code both backends share. It picks the task's job area, checks that the task's EOS output directory is empty, and writes the resolved content and `task.json`. It also holds `chunk`, which splits input files into condor jobs.

`condor.py`: The condor backend.

`crab.py`: The CRAB backend.

See `ntupleProduction/README.md` for choosing a backend, what a job area holds and where the output lands.

## Caveats

- A task's jobs and every retry run the resolved content and the copies of `ntuple_cfg.py` and `ntupleTables.py` that `submit` put in its job area, so a fix to a preset or to either file reaches only a new task.
