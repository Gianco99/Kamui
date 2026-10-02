# NtupleProduction

The first stage of the analysis: a DAS dataset in, ntuples out.

## What Lives Here

| Path | What it is |
| --- | --- |
| `cmssw/ntuple_cfg.py` | The `cmsRun` configuration |
| `cmssw/ntupleTables.py` | Turns the content JSON a job receives into CMSSW table producers |
| `jobs/<task>/` | Generated job areas, one per task. Gitignored |
| `.dasCache/` | Cached DAS responses. Gitignored |

The submission code is in `python/kamui/submit/`.

## Choosing A Backend

- **condor** for a fast answer: a new preset, a handful of files, a private dataset CRAB is awkward about. It asks DAS for the file list up front, reads inputs over the global redirector, and has no automatic retries.
- **CRAB** for a full production. One task per sample, sent to sites that already hold the data, splitting and retrying on its own.

## Running One Job By Hand

Before submitting to a cluster, it is worth running things locally to make sure they work. Write out the preset as a job receives it, then run the same `cmsRun` command the workers run. An example for the `dvSignal` preset:

```
./kamui content dvSignal --era Summer24 --write /tmp/dvSignal.json
cmsRun ntupleProduction/cmssw/ntuple_cfg.py content=/tmp/dvSignal.json isMC=True inputFiles=root://cmseos.fnal.gov//store/.../file.root outputFile=test.root maxEvents=1000
```

Note: Content with the vertexing collections also needs `globalTag=`, the era's tag from `config/sites.json`.
## What A Job Area Contains

`jobs/<task>/`:

| File | Backend | What it is |
| --- | --- | --- |
| `task.json` | both | The provenance record. Condor also records the cluster, the schedd and one entry per retry |
| `<preset>.<mc\|data>.<era>.json` | both | The preset written out in full, as the `cmsRun` job receives it. One per preset, MC or data, and era |
| `crabConfig_<sample>.py` | CRAB | One per sample |
| `crab/crab_<task>__<sample>/` | CRAB | The work area `crab status` and `crab resubmit` are pointed at |
| `fileLists.json` | condor | For each sample, the input files each job reads |
| `jobList.txt` | condor | One `sample,index,script` row per job |
| `runJob_<preset>_<mc\|data>_<era>.sh` | condor | The script a worker runs. One per content file above |
| `submit.jdl` | condor | What `condor_submit` is given |
| `logs/` | condor | `<sample>_<index>.out`, `.err`, and `condor.log` |

## Where The Output Lands

`config/sites.json` holds one output base for condor and a separate one for CRAB, and `--outputBase` overrides either.

| | condor | CRAB |
| --- | --- | --- |
| Base | `/store/user/lpcdisplacedvertices/$USER` | `/store/user/$USER/Kamui` |
| Ntuples | `<base>/ntuples/<task>/<sample>/<sample>_ntuple_<index>.root` | Under `<base>/ntuples/<task>/`, with the output dataset tag set to the sample name |
| Provenance | `<base>/ntuples/<task>/task.json` | `<base>/ntuples/<task>/task.json` |

`task.json` is copied to EOS at submit, so someone inspecting the output ROOT files can still find out where they came from:

- The commit and branch
- Whether the repo had uncommitted changes
- Who submitted it and when
- The CMSSW release
- The dataset and era behind every sample
- The full content the jobs received

## Relevant Commands

- Use `submit` to produce ntuples, `status` to watch a task, and `resubmit` to retry what failed.
- Run `check` before submitting. It validates every config offline and needs no proxy.
- Before writing a preset for a new campaign, use `tools/inspectMiniAOD.py` to see what its MiniAOD files carry.

See `python/kamui/README.md` for the flags and worked examples.

## Caveats
 
- Any collection whose key contains `genweight`, ignoring case, runs outside the skim so it sees every event. This is how the gen-weight table is picked out.
- Condor jobs set up the CMSSW release named in `config/sites.json`. Do not bump it without checking. CRAB ignores it and uses the release you submit from.
- The schedd is recorded at submit time so kamui asks the right one later. LPC spreads a submission across schedds and `condor_q` asks the default one, so a task submitted elsewhere would otherwise read as finished. A `task.json` with no `schedd` key falls back to the default.
