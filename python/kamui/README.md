# Kamui CLI Documentation

Kamui is the CLI for the whole analysis framework. Every stage of the analysis is meant to be driven through it, so there is one place to look for all of our analysis needs. It relies on a set of configuration files so we are never editing or hard-coding things into our scripts.

Two stages are implemented:

- Sample processing, which turns CMS datasets into analysis ntuples on EOS
- Event selection, which applies a selection config to those ntuples and writes ntuples with the same branches.

```
./kamui <command> [flags]
```

`./kamui <command> --help` prints the flags for one command.


## Picking samples

Before going into the documentation for each command, note that six commands accept the same five flags:
| Flag | What it matches |
| --- | --- |
| `--name NAME` (optional, default: None) | Exact sample name, repeatable |
| `--family NAME` (optional, default: None) | The `family` key of a file in `config/samples/` |
| `--era NAME` (optional, default: None) | Data-taking period |
| `--tag NAME` (optional, default: None) | A tag from the sample config |
| `--match PATTERN` (optional, default: None) | Wildcard on the sample name |



The commands that take them are `list`, `query`, `stage`, `submit`, `select` and `norm`.

Two things to keep in mind:

- An unknown `--name`, `--tag` or `--family` is always an error, on every command.

- An empty selection exits on all but `list`, which reports nothing found and carries on.

## Commands

### Initial framework setup

#### check

Validates the configs and the framework locally. It can be divided into config and architecture checks.

**Config Checks:**

| Check | What it means |
| --- | --- |
| Catalog | Every sample is listed once and is well-formatted |
| Content presets | Validated the format of each preset |
| Selections | Validated the format of every cut |
| Triggers | Every trigger file is parseable |
| Era isolation | Run 2 and Run 3 keep separate copies of content files |
| Generator sums | Samples that know their total generator weight |
| Sites and CMSSW | Validated `sites.json` and the CMSSW job script configurations |

**Architecture Checks:**
| Check | What it means |
| --- | --- |
| Layering | `foundations/` does not import from the rest of the framework (avoid circular imports) |
| Config access | `configReaders/` is the only folder containing config access scripts |

Each line is marked with a status.

- A cross is a failure
- A warning is something incomplete

Run it after editing any config, and before submitting anything. It exits non-zero when it finds a problem.
```
./kamui check
```

### Registering a Sample

#### find

Searches DAS for datasets matching a wildcard, regardless of whether we have them in our configs.

| Flag | Meaning |
| --- | --- |
| **`pattern`** (required, default: None) | Positional |
| `--instance INSTANCE` (optional, default: ) | `prod/global` for central datasets, `prod/phys03` for USER-created datasets |
| `--refresh` (optional, default: None) | Bypass the DAS cache |

```
./kamui find '/*HAHM*/*/MINIAODSIM'                       Everything from one model, any campaign
./kamui find '/*Hto2Sto4D*/RunIII2024*/MINIAODSIM'        One signal family in one campaign
./kamui find '/*Stealth*/*/USER' --instance prod/phys03   Privately produced datasets
```

#### norm

Records the generator weight sum for normalization in `config/normalizations/generatorSums.json`. The sums are read from the sample's central NanoAOD.

See `config/normalizations/README.md` for the files this writes into.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See above |
| `--write` (optional, default: None) | Write results to the JSON |
| `--refresh` (optional, default: None) | Bypass the DAS cache |

```
./kamui norm --family tutorial            Report the sums, write nothing
./kamui norm --family tutorial --write    Record them
./kamui norm --tag validation --write     A whole tag at once
```

A sample whose dataset has no central NanoAOD is skipped. This functionality should be updated at some point!

Use `./kamui check` to see how many cataloged samples have a sum recorded.

### Working with Registered Samples

#### list

Shows the samples in your config files, grouped by family. Four columns:

- The sample name
- The era
- The content preset it uses
- The tags it uses

| Flag | Meaning |
| --- | --- |
| The five sample flags | See above |
| `--datasets` (optional, default: None) | Print the bare DAS paths instead of the table |

```
./kamui list                                       Everything
./kamui list --name rpvStopDD_M400_ctau1mm_2018    One exact sample
./kamui list --family rpv2024                      Everything in one sample config file
./kamui list --era 2018                            Everything in one era
./kamui list --tag validation                      One tag (a sample can carry several!)
./kamui list --match 'ggH-*ctau10mm*'              Glob on the sample name
./kamui list --tag rpv --era 2018                  Combining different paths
./kamui list --tag validation --datasets           Just the DAS paths
```

#### query

Asks DAS how many files, events and gigabytes each selected sample holds, and totals them. Needs cmsenv and a valid grid proxy. Answers are cached.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See above |
| `--refresh` (optional, default: None) | Ignore the cache and ask DAS again |

```
./kamui query --tag validation                     The 24 Run 2 samples
./kamui query --family exoticHiggs4d2024           A whole family
./kamui query --tag rpv --refresh                  Ignore the cache
```

#### stage

Copies raw MiniAOD from the grid to our EOS area, for local tests. It copies the whole dataset unless `--maxFiles` caps it.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See above |
| `--maxFiles N` (optional, default: None) | Cap on files copied |
| `--dryRun` (optional, default: None) | Print what would be copied, copy nothing |
| `--refresh` (optional, default: None) | Bypass the DAS cache |

```
./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024             One whole sample
./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024 --dryRun    Print what would be copied
./kamui stage --tag rpv --maxFiles 1                          One file each
```

### Defining Our Ntuples

#### content

Shows what a content preset would write into your ntuples, without running anything.

See `config/content/README.md` for how a collection or preset is written, and `config/triggers/README.md` for the channel a `skim` names.

One row per collection:

- Its name
- What kind of object it is
- Which MiniAOD collection it comes from
- How many variables are kept
- Any cut or cap.

| Flag | Meaning |
| --- | --- |
| `preset` (optional, default: None) | Positional. The preset or collection to resolve. Omit it to list them |
| `--data` (optional, default: None) | Resolve as data, which drops the `mcOnly` collections |
| `--era NAME` (optional, default: `Summer24`) | Era whose content set to resolve against |
| `--write PATH` (optional, default: None) | Write the resolved JSON to this path |
```
./kamui content                                    The presets run2 and run3 define
./kamui content dvSignal                           What a preset resolves to
./kamui content jets                               A single collection on its own
./kamui content dvSignal --data                    The generator collections disappear
./kamui content dvLepton --era 2018                A Run 2 preset
./kamui content dvFull --write resolved.json       Write out exactly what a job would be handed
```

### Producing the Ntuples

See `ntupleProduction/README.md` for more details on job submission. This section just describes how to run the submission via the CLI.

#### submit

Produces the ntuples. It takes the samples you selected, works out what each job should write, builds a job area on disk, and sends it to condor or to CRAB.

See `config/content/README.md` for what a preset decides to save.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See above |
| **`--task NAME`** (required, default: None) | Names the directory under `ntupleProduction/jobs/` and the EOS output subdirectory |
| `--backend BACKEND` (optional, default: `condor`) | `condor` or `crab` |
| `--content NAME` (optional, default: None) | Override the content preset the selected samples use |
| `--filesPerJob N` (optional, default: the sample's `unitsPerJob`, else 5) | Input files per job |
| `--maxFiles N` (optional, default: None) | Use at most this many input files per sample |
| `--memoryMB N` (optional, default: 2500) | Memory request per job |
| `--dryRun` (optional, default: None) | Write the job area, submit nothing |
| `--refresh` (optional, default: None) | Bypass the DAS cache |
| `--overwrite` (optional, default: None) | Overwrite an existing job area without asking |
| `--outputBase PATH` (optional, default: the site stageout base) | Write output under this EOS path |
```
./kamui submit --tag validation --task run2Val --dryRun                               Build the job area, submit nothing
./kamui submit --tag validation --task run2Val --backend crab                         The 24 Run 2 samples at LPC, through CRAB
./kamui submit --tag rpv --task rpvNtuples --content dvFull                           Override the preset every sample uses
./kamui submit --tag rpv --task big --filesPerJob 10 --memoryMB 4000                  Fewer, larger, hungrier jobs
./kamui submit --name ggH-2S-4D_mS15_ctau1mm_2024 --task quick --maxFiles 2           Two files only, for a fast test
./kamui submit --tag rpv --task elsewhere --outputBase /store/user/gdecastr/Scratch   Output somewhere other than the default
```

#### status

Reports how a submitted production task is doing. It reads the job area, sees which backend produced it, and asks that backend.

| Flag | Meaning |
| --- | --- |
| **`--task NAME`** (required, default: None) | A task under `ntupleProduction/jobs/` |

```
./kamui status --task run2Val
```

#### resubmit

Resubmits only the jobs of a task whose outputs never reached EOS. On CRAB it asks CRAB to retry its own failed jobs. On condor it compares what is on EOS against what the task expected.

| Flag | Meaning |
| --- | --- |
| **`--task NAME`** (required, default: None) | The task to retry |
| `--dryRun` (optional, default: None) | Report what would be resubmitted, submit nothing |
| `--forceResubmit` (optional, default: None) | Resubmit even while jobs from this task are still queued |
```
./kamui resubmit --task run2Val --dryRun           What is missing
./kamui resubmit --task run2Val                    Retry it
```

### Applying Selections

#### select

Applies an event-level selection to ntuples a `submit` task produced, and writes ntuples with the same branches.

See `config/selections/README.md` for how a cut is written.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See above |
| **`--selection NAME`** (required, default: None) | A config in `config/selections/` |
| **`--task NAME`** (required, default: None) | Names this selection pass |
| **`--inputTask NAME`** (required, default: None) | The ntuple production task to read from |
| `--inputBase PATH` (optional, default: the site stageout base) | EOS base holding the input ntuples |
| `--outputBase PATH` (optional, default: the site stageout base) | Where to write the selected ntuples |
| `--backend BACKEND` (optional, default: `local`) | `local` or `condor` |
| `--filesPerJob N` (optional, default: 5) | Input files per job on condor |
| `--dryRun` (optional, default: None) | Write the job area, submit nothing |

Output carries the same branches as input, so a selection can be applied to an earlier pass's output.
```
./kamui select --tag leptonTriggered --selection run2Lepton --task lepPass --inputTask run2Val                                 Run it locally
./kamui select --tag displacementTriggered --selection run2Displaced --task dispPass --inputTask run2Val --backend condor      Send it to the cluster
```

#### cutflow

Prints the cutflow a local `select` task recorded. Per cut, it quotes:

- The events kept
- The events removed
- The step efficiency
- The cumulative efficiency

The first row is `generated`, the events in the whole dataset as `norm` recorded them. A sample with no recorded sum has no such row and the table starts at the ntuple.

| Flag | Meaning |
| --- | --- |
| **`--task NAME`** (required, default: None) | The select task |

```
./kamui cutflow --task lepPass
```

### DAS Cache

#### cache

Describes the DAS cache, or thins it out. DAS is slow, so every answer `find`, `query`, `norm` and `submit` get back is kept on disk and reused. Prints how many responses are held, how much space they take, how old they are, and how many have passed the 30 day age limit.

| Flag | Meaning |
| --- | --- |
| `--prune` (optional, default: None) | Delete expired entries |
| `--clear` (optional, default: None) | Delete every cached response |

```
./kamui cache                                      What is cached right now
./kamui cache --prune                              Drop the expired entries
./kamui cache --clear                              Throw the whole thing away
```

## The Code Behind It

`cli.py` is the driver. Each subfolder has its own `README.md` and `CLAUDE.md`:

| Folder | What it does |
| --- | --- |
| `foundations/` | The bottom layer everything is built on |
| `configReaders/` | The only folder that opens config files |
| `grid/` | Everything that reaches outside our own machine |
| `submit/` | Building and sending job areas |
| `select/` | Applying a selection to ntuples |
| `helpers/` | Extras |
