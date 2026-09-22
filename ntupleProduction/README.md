# NtupleProduction

The first stage of the analysis: a DAS dataset in, ntuples out.

## What Lives Here

| Path | What it is |
| --- | --- |
| `cmssw/ntuple_cfg.py` | The `cmsRun` configuration |
| `cmssw/ntupleTables.py` | Turns a resolved content JSON into CMSSW table producers |
| `jobs/<task>/` | Generated job areas, one per task. Gitignored |
| `.dasCache/` | Cached DAS responses. Gitignored |

The submission code is in `python/kamui/submit/`, and the configs it reads are in `config/`. See `python/kamui/README.md` for the commands and their flags.

## Choosing A Backend

- **condor** for a fast answer: a new preset, a handful of files, a private dataset CRAB is awkward about. It asks DAS for the file list up front, reads inputs over the global redirector, and has no automatic retries.
- **CRAB** for a full production. One task per sample, sent to sites that already hold the data, splitting and retrying on its own.

## Running One Job By Hand

Before submitting to a cluster, it is worth running things locally to make sure they work. Flatten a preset, then run the same `cmsRun` command the workers run. An example for the `dvSignal` preset:

```
./kamui content dvSignal --era Summer24 --write /tmp/dvSignal.json
cmsRun cmssw/ntuple_cfg.py content=/tmp/dvSignal.json isMC=True inputFiles=root://cmseos.fnal.gov//store/.../file.root outputFile=test.root maxEvents=1000
```

Needs `cmsenv`. See `config/content/README.md` for what a preset declares. 
## What A Job Area Contains

`jobs/<task>/`:

| File | Backend | What it is |
| --- | --- | --- |
| `task.json` | both | The provenance record. Condor also records the cluster, the schedd and one entry per retry |
| `<preset>.<mc\|data>.<run2\|run3>.json` | both | The flattened content, what the `cmsRun` job receives. One per preset, flavor and era set |
| `crabConfig_<sample>.py` | CRAB | One per sample |
| `crab/crab_<task>__<sample>/` | CRAB | The work area `crab status` and `crab resubmit` are pointed at |
| `fileLists.json` | condor | Sample name to the list of input files each job index gets |
| `jobList.txt` | condor | One `sample,index,script` row per job |
| `runJob_<preset>_<mc\|data>_<run2\|run3>.sh` | condor | The script a worker runs. One per content file above |
| `submit.jdl` | condor | What `condor_submit` is given |
| `logs/` | condor | `<sample>_<index>.out`, `.err`, and `condor.log` |

## Where The Output Lands

`config/sites.json` holds the two bases. Condor writes to the shared `lpcdisplacedvertices` area, CRAB into your own `/store/user`, and `--outputBase` moves either.

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
- The fully resolved content

## Relevant Commands

- Use `submit` to produce ntuples, `status` to watch a task, and `resubmit` to retry what failed.
- Run `check` before submitting. It validates every config offline and needs no proxy.
- Use `tools/inspectMiniAOD.py` to see what a MiniAOD file embeds before writing a preset against a new campaign.

See `python/kamui/README.md` for the flags and worked examples.
