# NtupleProduction

This folder is the first stage of the analysis: a DAS dataset goes in and ntuples come out. `./kamui submit` turns the samples you pick into a task, a named batch of jobs that runs on condor or CRAB. Every job runs `cmssw/ntuple_cfg.py` with its sample's content preset, the JSON that says what the ntuples save. Each task gets a job area, `jobs/<task>/`, holding the files its jobs are built from.

For example, this writes the job area `jobs/myNtuples/` for the Summer24 samples matching the pattern, and submits nothing:

```
./kamui submit --task myNtuples --match 'ggH*ctau10mm*' --era Summer24 --dryRun
```

## What Lives Here

| Path | What it is |
| --- | --- |
| `cmssw/ntuple_cfg.py` | The `cmsRun` configuration |
| `cmssw/ntupleTables.py` | Turns the content JSON a job receives into CMSSW table producers |
| `jobs/<task>/` | Generated job areas, one per task. Gitignored |
| `.dasCache/` | Cached DAS responses. Gitignored |

The submission code is in `python/kamui/submit/`.

## Choosing a Backend

- Use condor for a fast answer: a new preset, a handful of files, or a private dataset CRAB is awkward about. It asks DAS for the file list up front, reads the inputs through `sourceRedirector` from `config/sites.json`, and has no automatic retries.
- Use CRAB for a full production. It makes one CRAB task per sample, runs the jobs at sites that already hold the data, and splits and retries them by itself.

## Running One Job by Hand

Before you submit to a cluster, run one job locally to make sure it works. First save the preset with `./kamui content --write`, which writes the same file a job receives, with every include and per-era value filled in. Then run the same `cmsRun` command the workers run. For the `dvSignal` preset:

```
./kamui content dvSignal --era Summer24 --write /tmp/dvSignal.json
cmsRun ntupleProduction/cmssw/ntuple_cfg.py content=/tmp/dvSignal.json isMC=True inputFiles=root://cmseos.fnal.gov//store/.../file.root outputFile=test.root maxEvents=1000
```

Setting `maxEvents` adds it to the output name, so this writes `test_numEvent1000.root`.

Content with the vertexing collections also needs `globalTag=`, set to the era's tag from `config/sites.json`. Data with a lumi mask also needs `lumiMask=`, set to the mask JSON.

## What a Job Area Contains

Everything below sits in `jobs/<task>/`.

| File | Backend | What it is |
| --- | --- | --- |
| `task.json` | both | The provenance record. It holds `outputDir`, the EOS directory the output lands in. Condor also records the cluster, the schedd and one entry per retry. CRAB also records which samples were submitted and which failed to submit |
| `<preset>.<mc\|data>.<era>.json` | both | The preset written out in full, as the `cmsRun` job receives it. There is one for each combination of preset, MC or data, and era |
| `ntuple_cfg.py`, `ntupleTables.py` | both | Copies of the `cmssw/` files taken at submit. The jobs and their retries run these copies |
| `crabConfig_<sample>.py` | CRAB | One per sample |
| `crab/crab_<task>__<sample>/` | CRAB | The work area you point `crab status` and `crab resubmit` at |
| `fileLists.json` | condor | For each sample, the input files each job reads |
| `lumiMasks.json`, `lumiMask<n>.json` | condor | Which lumi mask each masked sample's jobs apply, and the masks themselves. Written only when a sample has one |
| `jobList.txt` | condor | One `sample,index,script` row per job |
| `runJob_<preset>_<mc\|data>_<era>.sh` | condor | The script a worker runs. One per content file above |
| `cmsswArea.tar.gz` | condor | The compiled code of your CMSSW area (`lib/`, `python/`, `cfipython/`). Each worker unpacks it into its fresh release |
| `submit.jdl` | condor | The file `condor_submit` is given |
| `logs/` | condor | `<sample>_<index>.out`, `.err`, and `condor.log` |
| `submit.retry<n>.jdl`, `jobList.retry<n>.txt`, `logs/retry<n>/` | condor | What retry `<n>` of `./kamui resubmit` adds: its JDL, the jobs it reruns and their logs |

## Where the Output Lands

`config/sites.json` holds one output base for condor and another for CRAB, and `--outputBase` overrides either.

| | condor | CRAB |
| --- | --- | --- |
| Base | `stageoutBase` | `crabStageoutBase` |
| Ntuples | `<base>/ntuples/<task>/<sample>/<sample>_ntuple_<index>.root` | Under `<base>/ntuples/<task>/`, with the output dataset tag set to the sample name |
| Provenance | `<base>/ntuples/<task>/task.json` | `<base>/ntuples/<task>/task.json` |

`task.json` is copied to EOS at submit, so anyone looking at the output ROOT files can still find out where they came from. It records:

- The commit and branch
- Whether the repo had uncommitted changes
- Who submitted it and when
- The CMSSW release
- The dataset and era behind every sample
- The full content the jobs received

## Relevant Commands

- `./kamui submit` produces ntuples, `./kamui status` shows how a task is doing, and `./kamui resubmit` retries what failed.
- Run `./kamui check` before submitting. It validates every config offline and needs no proxy.
- Before writing a preset for a new campaign, run `tools/inspectMiniAOD.py` to see what its MiniAOD files carry.

The flags and worked examples are in `python/kamui/README.md`.
