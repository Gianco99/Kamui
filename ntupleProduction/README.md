# ntupleProduction

The first stage of the analysis: a DAS dataset in, flat ROOT ntuples on EOS out. One `cmsRun` job reads MiniAOD, builds the tables named by a content preset, and writes an `Events` tree that uproot and RDataFrame can read without CMSSW. Everything downstream reads those files.

## What lives here

| Path | What it is |
| --- | --- |
| `cmssw/kamuiNtuple_cfg.py` | The `cmsRun` configuration. Wiring only: every content decision arrives in the resolved content JSON it is handed. |
| `cmssw/kamuiTables.py` | Turns that JSON into the CMSSW table producers. The only file here that knows plugin names. |
| `cmssw/inspectMiniAOD.py` | Reports the b-tag discriminators, embedded lepton IDs and userFloats a given MiniAOD file actually carries. |
| `jobs/<task>/` | Generated job areas, one per task. Gitignored. |
| `branchDumps/` | Saved `edmDumpEventContent` output, kept as a reference for what a MiniAOD file contains. Gitignored. |

The submission code is in `../python/kamui/submit/`, and the sample, content and site configs it reads are in `../config/`.

## Before you submit

From a `CMSSW_16_1_2` release area, with `cmsenv` done and a valid proxy:

```
voms-proxy-init --rfc --voms cms -valid 192:00
./kamui check
```

`check` validates every config offline and exits non-zero when something does not add up. The release and architecture the jobs use come from `../config/sites.json`.

## Submitting

```
./kamui submit --tag signal --task run3Signal --backend condor --dry-run
./kamui submit --tag signal --task run3Signal --backend condor
```

Pick samples with the usual five flags, `--name` (repeatable), `--family`, `--era`, `--tag` and `--match`. The rest:

| Flag | Effect |
| --- | --- |
| `--task` | Required. Names the job area under `jobs/` and the output subdirectory on EOS. Letters, digits, dot, dash and underscore, at most 96 characters. |
| `--backend` | `condor` (default) or `crab`. |
| `--content` | Override the content preset every selected sample would otherwise use. |
| `--output` | `ntuple` (default), `miniaod`, or `both`. The last two need a preset that defines a `miniaod` block. |
| `--filesPerJob` | Input files per job. Beats a sample's own `unitsPerJob`; five when neither says anything. |
| `--maxFiles` | Cap on how many input files a sample uses at all. |
| `--memoryMB` | Memory request per job, 2500 by default. |
| `--outputBase` | EOS base to write under, overriding the site default. |
| `--refresh` | Bypass the DAS cache. |
| `--yes` | Overwrite an existing job area without asking. |
| `--dry-run` | Write the whole job area, submit nothing. |

Both backends write the job area to disk first and submit second, so a `--dry-run` leaves you the exact files that would have run.

Reusing a task name asks before it overwrites, and answering no writes to `<task>_2`. A task area holding a CRAB work area or a recorded condor cluster is never overwritten, because its jobs may still be running.

### condor

Runs at LPC. `submit` asks DAS for the file list, chunks it, and writes one row per job into `jobList.txt`. Each job sets up CMSSW from cvmfs, reads its inputs over xrootd from wherever they live, and copies its own output to EOS with `xrdcp`. There are no automatic retries, and the jobs run at FNAL whatever site holds the data, so a dataset with no copy here reads slowly. This is the backend for a fast answer: debugging a new preset, a handful of files, a private dataset, or reprocessing what is already staged on our EOS.

### CRAB

One CRAB task per sample, `FileBased` splitting. CRAB sends each job to a site that already holds the data, does its own splitting and retries its own failures, so nothing here has to ask DAS which files exist. This is the backend for a full production over many datasets.

## Where the output lands

`../config/sites.json` holds the two bases. Condor writes to the shared `lpcdisplacedvertices` area; CRAB writes into your own `/store/user`. `--outputBase` moves either one.

| | condor | CRAB |
| --- | --- | --- |
| Base | `/store/user/lpcdisplacedvertices/$USER` | `/store/user/$USER/Kamui` |
| Ntuples | `<base>/ntuples/<task>/<sample>/<sample>_ntuple_<index>.root` | under `<base>/ntuples/<task>/`, in CRAB's own subdirectory layout, with the output dataset tag set to the sample name |
| Slimmed MiniAOD | `<base>/ntuples/<task>/<sample>/<sample>_miniaod_<index>.root` | alongside the ntuples of the same task |
| Provenance | `<base>/ntuples/<task>/task.json` | `<base>/ntuples/<task>/task.json` |

`task.json` is copied to EOS at submit so that someone holding only the ROOT files can still find out where they came from: the commit and branch, whether that tree was dirty, who submitted it and when, the CMSSW release, the dataset and era behind every sample, and the fully resolved content.

## What a job area contains

`jobs/<task>/`:

| File | Backend | What it is |
| --- | --- | --- |
| `task.json` | both | The provenance record, plus the condor cluster and schedd, plus one entry per retry. |
| `<preset>.mc.json`, `<preset>.data.json` | both | The flattened content, byte for byte what the `cmsRun` job receives. |
| `crabConfig_<sample>.py` | CRAB | One per sample. |
| `crab/crab_<task>__<sample>/` | CRAB | The work area `crab status` and `crab resubmit` are pointed at. |
| `fileLists.json` | condor | Sample name to the list of input files each job index gets. |
| `jobList.txt` | condor | One `sample,index,script` row per job. |
| `runJob_<preset>_<mc\|data>_<era>.sh` | condor | The script a worker runs. One per content preset, data/MC flavour and era, since each combination resolves to different content. |
| `submit.jdl` | condor | What `condor_submit` is given. |
| `logs/` | condor | `<sample>_<index>.out`, `.err`, and `condor.log`. |

## Watching a task

```
./kamui status --task run3Signal
```

It reads the job area, works out which backend produced it, and asks that backend: `crab status` over every project, or `condor_q` against the cluster and schedd recorded at submit time. It also prints the provenance line and the EOS output directory.

## Resubmitting

```
./kamui resubmit --task run3Signal --dry-run
./kamui resubmit --task run3Signal
```

For condor, this lists what is actually on EOS under the task's output directory and compares it against `jobList.txt`, one expected filename per job (two when the task was submitted with `--output both`). Jobs whose output is not there are the ones that failed, whatever the reason, and only those are resubmitted:

```
outputs  118/120 present on EOS
missing  2 job(s):
           ggH-2S-4D_mS55_ctau10mm_2024  job 7
           ggH-2S-4D_mS55_ctau10mm_2024  job 19
```

The retry reuses the task area untouched, so the same run scripts, the same resolved content and the same EOS destination apply and the retried files land beside the ones that already succeeded. What is new is `jobList.retryN.txt`, `submit.retryN.jdl` and `logs/retryN/`, so the first attempt's logs survive for as long as you want to read them. `N` counts up from 1 over whatever the task has used before. The retry is appended to `task.json` under `retries`, and `status` prints one line per retry.

A `--dry-run` reports what would go and writes nothing, leaving the retry number free for the real attempt.

Jobs still on the queue have not failed, and rerunning one would write the same output filename twice, so `resubmit` stops when it finds any of the task's jobs still queued or running. `--yes` overrides that.

For a CRAB task this runs `crab resubmit` over every project in the work area. CRAB tracks its own failed jobs and writes their output to the same place, so there is nothing to reconstruct.

## Running one job by hand

Flatten a preset, then run the same `cmsRun` command the workers run:

```
./kamui content dvSignal --write /tmp/dvSignal.json
cmsRun cmssw/kamuiNtuple_cfg.py content=/tmp/dvSignal.json isMC=True \
    inputFiles=root://cmseos.fnal.gov//store/.../file.root \
    outputFile=test.root maxEvents=1000
```

`globalTag`, `nThreads` and `reportEvery` are the other options it takes. Conditions are loaded only when a global tag is given, since every table built so far reads quantities already stored in MiniAOD.

## Checking what a file contains

A wrong electron ID name throws at runtime and a wrong b-tag name quietly returns -1000, and both move between campaigns. Before writing a content preset against a new campaign:

```
python3 cmssw/inspectMiniAOD.py root://cmseos.fnal.gov//store/.../file.root
```

It prints the b-tag discriminators, embedded IDs, userFloats and userInts from the first event that has the collection. `--branches` adds `edmDumpEventContent`. It needs `cmsenv` and nothing else for files already on our EOS.
