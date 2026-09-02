# ntupleProduction

The first stage of the analysis: a DAS dataset in, ntuples out.

## What Lives Here

| Path | What it is |
| --- | --- |
| `cmssw/kamuiNtuple_cfg.py` | The `cmsRun` configuration |
| `cmssw/kamuiTables.py` | Turns a resolved content JSON into CMSSW table producers |
| `jobs/<task>/` | Generated job areas, one per task. Gitignored |

The submission code is in `../python/kamui/submit/`, and the configs it reads are in `../config/`. The rest of this README documents some of the information to consider when submitting a job.

## Choosing A Backend

- **condor** runs at LPC. 
  - `submit` asks DAS for the file list and chunks it. Then, each job sets up CMSSW from cvmfs, reads its inputs over xrootd from wherever they live, and copies its output to EOS with `xrdcp`. 
  - Use it for a fast answer: a new preset, a handful of files, or reprocessing what is already on our EOS.

- **CRAB** runs one task per sample with `FileBased` splitting. 
  - It sends each job to a site that already holds the data, does its own splitting and retries its own failures. 
  - Use it for a full production over many datasets.

## Running One Job By Hand

Before submitting to a cluster, it is worth running things locally to make sure they work! To do so, flatten a preset, then run the same `cmsRun` command the workers run. An example for the `dvSignal`preset is given below:
```
./kamui content dvSignal --write /tmp/dvSignal.json
cmsRun cmssw/kamuiNtuple_cfg.py content=/tmp/dvSignal.json isMC=True inputFiles=root://cmseos.fnal.gov//store/.../file.root outputFile=test.root maxEvents=1000
```
## What A Job Area Contains

`jobs/<task>/`:

| File | Backend | What it is |
| --- | --- | --- |
| `task.json` | both | The provenance record, the condor cluster and schedd, and one entry per retry |
| `<preset>.mc.json`, `<preset>.data.json` | both | The flattened content, what the `cmsRun` job receives |
| `crabConfig_<sample>.py` | CRAB | One per sample |
| `crab/crab_<task>__<sample>/` | CRAB | The work area `crab status` and `crab resubmit` are pointed at |
| `fileLists.json` | condor | Sample name to the list of input files each job index gets |
| `jobList.txt` | condor | One `sample,index,script` row per job |
| `runJob_<preset>_<mc\|data>_<era>.sh` | condor | The script a worker runs. One per preset, data/MC flavor and era, since each combination resolves to different content |
| `submit.jdl` | condor | What `condor_submit` is given |
| `logs/` | condor | `<sample>_<index>.out`, `.err`, and `condor.log` |

Both backends write the job area to disk before submitting, so a dry run leaves the exact files that would have run for debugging.

## Where The Output Lands

`../config/sites.json` holds the two bases. Condor writes to the shared `lpcdisplacedvertices` area, CRAB into your own `/store/user`, and `--outputBase` moves either.

| | condor | CRAB |
| --- | --- | --- |
| Base | `/store/user/lpcdisplacedvertices/$USER` | `/store/user/$USER/Kamui` |
| Ntuples | `<base>/ntuples/<task>/<sample>/<sample>_ntuple_<index>.root` | under `<base>/ntuples/<task>/`, with the output dataset tag set to the sample name |
| Provenance | `<base>/ntuples/<task>/task.json` | `<base>/ntuples/<task>/task.json` |

`task.json` is copied to EOS at submit, so someone inspecting the output ROOT files can still find out where they came from: 

- The commit and branch
- Whether that tree was dirty
- Who submitted it and when
- The CMSSW release
- The dataset and era behind every sample
- The fully resolved content.

## How A Retry Works

For condor, `resubmit` lists what is on EOS under the task's output directory and compares it against `jobList.txt`. Jobs whose output is not there are the ones that failed and only those go again. An example is given below:
```
outputs  118/120 present on EOS
missing  2 job(s):
           ggH-2S-4D_mS55_ctau10mm_2024  job 7
           ggH-2S-4D_mS55_ctau10mm_2024  job 19
```

The retry reuses the task area without changing anything, so the retried files land beside the ones that succeeded. However, a new `jobList.retryN.txt`, `submit.retryN.jdl` and `logs/retryN/` are written so that earlier logs survive.


Jobs still queued are not considered to have  failed, so `resubmit` stops when it finds any of the task's jobs are still queued or running.

For a CRAB task, it runs `crab resubmit` over every project. CRAB tracks its own failed jobs and writes to the same place, so there is nothing to reconstruct.

## Relevant Commands

- Use `submit` to produce ntuples, `status` to watch a task, and `resubmit` to retry what failed.
- Run `check` before submitting. It validates every config offline and needs no proxy.

See Kamui/python/kamui/README.md for the flags and worked examples.

Bonus: Use `tools/inspectMiniAOD.py` to see what a MiniAOD file embeds before writing a content preset against a new campaign.
