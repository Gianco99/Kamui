# submit/

Everything that turns a set of samples into running jobs. Each backend first writes a job area to disk and only then submits, so a `--dryRun` leaves you the exact files that would have been used.

A job area is one directory per task, under `ntupleProduction/jobs/<task>/`, holding everything a job needs.

`common.py` - The parts both backends share: making the task directory, flattening the content preset into it, splitting a file list into per-job groups, and writing `task.json`.

`condor.py` - The default backend. It runs at LPC, for when you want a fast answer on a handful of files: debugging a new preset, a private dataset CRAB is awkward about, or reprocessing what is already staged on our EOS. Because condor has no idea what a dataset is, this backend needs the file list up front, which is why `submit` asks DAS for it first. Jobs read their inputs over xrootd and copy the output back to EOS themselves. There are no automatic retries, and everything runs at FNAL no matter where the data lives, so a dataset with no copy here will read slowly. Use Rucio to replicate datasets if necessary.

`crab.py` - For large productions. It writes one crabConfig per sample and submits them one at a time. CRAB sends each job to a site that already holds the data, splits the dataset itself, and retries failures on its own, so we never have to ask DAS which files exist.

Every task also writes a provenance record, `task.json`, and copies it to EOS next to the ntuples when the jobs are really submitted. It is meant to be read later by someone who has only the ROOT files: it carries the commit and branch the task was submitted from, whether that tree had uncommitted changes, who submitted it and when, the CMSSW release, the dataset and era behind every sample, and the fully resolved content.

What lands in a job area:

| File | What it is |
| --- | --- |
| `task.json` | The provenance record described above, also copied to EOS |
| `<preset>.mc.json` | The flattened content config, exactly as the cmsRun job receives it |
| `crabConfig_<sample>.py` | CRAB only, one per sample |
| `fileLists.json` | Condor only, the input files each job gets |
| `jobList.txt` | Condor only, one row per job |
| `runJob_<preset>_<mc\|data>.sh` | Condor only, the script a worker runs |
| `submit.jdl` | Condor only, what `condor_submit` is given |
