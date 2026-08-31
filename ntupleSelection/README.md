# ntupleSelection

The second stage of Kamui. It reads the ntuples that `ntupleProduction` wrote, applies an event-level selection to them, and writes ntuples carrying the same branches as the ones it read. Nothing is dropped from an event: a cut either keeps the whole event or throws it away.

The code is in `python/kamui/select/`. This directory holds only what a run generates: `out/` for local output and cutflows, `jobs/` for condor job areas. Both are gitignored and both are created on demand, so a fresh clone has neither and nothing has to be set up by hand.

## Running a selection

```bash
./kamui select --tag validation --selection run2Lepton --task run2LepV1 --inputTask run2Val
```

That reads every ntuple the production task `run2Val` wrote for the samples tagged `validation`, applies the selection `run2Lepton` to each, and writes the results and a cutflow under `out/run2LepV1/`.

| Flag | Meaning |
| --- | --- |
| `--selection` | Required. The name of a config in `config/selections/`, without the `.json`. |
| `--task` | Required. Names this pass. It becomes the directory under `out/` or `jobs/`, and the output directory on EOS. |
| `--inputTask` | Required. The production task to read from. |
| `--inputBase` | Base path holding the input ntuples. Defaults to the site stageout base from `config/sites.json`. |
| `--outputBase` | Where the condor jobs write their output. |
| `--backend` | `local` (default) or `condor`. |
| `--cutflow` | Also write one ntuple per cut beside the output, named after the cut. Local only. |
| `--filesPerJob` | Input files per condor job. Five when not given. |
| `--dryRun` | Build the condor job area and submit nothing. |

Which samples are processed comes from the same five flags every sample command takes: `--name` (repeatable, exact), `--family`, `--era`, `--tag`, `--match`. A task name may use letters, digits, dot, dash and underscore, up to 96 characters, since it becomes a directory, an EOS path component and a shell word.

Inputs are found by walking `<inputBase>/ntuples/<inputTask>` and keeping every `.root` file whose path has the sample name as one of its directory components. That covers both layouts: condor writes `<task>/<sample>/`, and CRAB nests under `<task>/<primaryDataset>/<sample>/<timestamp>/0000/`. A sample with no files found is reported and skipped.

## Selections

A selection is one JSON file in `config/selections/`. It lists the eras it applies to and its cuts, in the order they are applied, which is also the order the cutflow reports. Thresholds, trigger lists and flag lists may be written as a single value or as an object keyed by era; `./kamui select` resolves one selection per era across the samples it was given, so a pass spanning 2016 through 2018 uses the right numbers for each.

## Backends

The local backend runs in the calling process and is a matter of seconds for a small pass. It reads every input file for a sample into memory at once, so it suits a handful of files per sample.

The condor backend writes a complete job area under `jobs/<task>/` and then submits it. The area holds `submit.jdl`, `jobList.txt` (one row of `sample,index,script`), `fileLists.json` (the input files each job reads), one `selection_<era>.json`, one `runSelect_<selection>_<era>.sh` per era, `kamuiPackage.tar.gz` with the framework in it, `task.json` recording what was submitted, and `logs/`. Each job sets up CMSSW from cvmfs, unpacks the framework, runs the selection over its share of the input files, and copies the result to EOS. `--dryRun` leaves the whole area on disk with nothing submitted, which is the way to read the exact configuration a job would use.

## Where output lands

| Backend | Output |
| --- | --- |
| local | `out/<task>/<sample>/<sample>_selected.root` |
| local | `out/<task>/cutflow.json`, covering every sample in the task |
| condor | `<outputBase>/selected/<task>/<sample>/<sample>_selected_<index>.root` on EOS |
| condor | `<outputBase>/selected/<task>/<sample>/<sample>_cutflow_<index>.json` on EOS, one per job |

## The cutflow

The cutflow is the record of how many events each cut kept. It opens with an `input` row counting what was read, then carries one row per cut with the events surviving, the events that cut removed, its own efficiency against the row above, and the cumulative efficiency against the input.

```bash
./kamui cutflow --task run2LepV1
```

Every row prints the cut's `doc` from the selection config and an `applied as` line describing what the cut actually matched in this file: how many of its trigger paths were present, which flags were missing, the bounds a quantity cut used, the events each alternative of an `anyOf` kept. That line is what distinguishes a cut that removed events from a cut that removed everything because the branch it wanted was not there. A task covering more than one sample ends with a combined table.

`./kamui cutflow` reads the local `out/<task>/cutflow.json`. A condor pass leaves its cutflows on EOS, one JSON per job, to be merged as needed.

## Repeating the stage

Output has the same branch structure as input, including the per-collection counter branches, so a selection can be applied to the output of an earlier selection. A tight selection can therefore be built as a loose common pass followed by a per-channel pass, and the second pass is the same command with the first pass's output as its input.

## Generator sums

`./kamui norm` lives with this stage. It stores the generator sums in `config/normalizations/generatorSums.json`, which is the denominator any yield computed from selected ntuples is normalized by. The sums describe the dataset as generated, so they are read from the sample's central NanoAOD rather than from anything we produced.
