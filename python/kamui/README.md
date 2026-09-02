# Kamui

Kamui is the CLI for the whole analysis framework. Every stage of the analysis is meant to be driven through it, so there is one place to look for all of our analysis needs. It relies on a set of configuration files so we are never editing or hard-coding things into our scripts.

Two stages are implemented: sample processing, which turns CMS datasets into analysis ntuples on EOS, and event selection, which applies a selection config to those ntuples and writes ntuples with the same branches.

```
./kamui <command> [flags]
./kamui --noBanner <command>     # --noBanner goes before the command
KAMUI_NO_BANNER=1                 # or set this once and never see it again
```

`./kamui <command> --help` prints the flags for one command.


## Picking samples

Six commands take the same five flags. `--name` may be repeated.

| Flag | What it matches |
| --- | --- |
| `--name` | Exact sample name, repeatable |
| `--family` | The sample config file, e.g. `exoticHiggs4d2024` |
| `--era` | Data-taking period: `2016`, `2016APV`, `2017`, `2018`, `Summer24` |
| `--tag` | A tag from the sample config, e.g. `validation`, `signal`, `leptonTriggered` |
| `--match` | Wildcard on the sample name; quote it or the shell eats it first |

The commands that take them are `list`, `query`, `stage`, `submit`, `select` and `norm`. Every one of them exits when nothing matched, except that `list` tolerates a `--match` that matches nothing. An unknown `--name`, `--tag` or `--family` is always an error.

## Commands

### Initial framework setup

#### check

Validates the configs and the framework locally.

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

Searches DAS for datasets matching a wildcard, whether or not we have them in our configs.

| Flag | Meaning |
| --- | --- |
| `pattern` | Positional, required. Put it in quotes! |
| `--instance` | `prod/global` for official datasets (default), `prod/phys03` for USER ones |
| `--refresh` | Bypass the DAS cache |

```
./kamui find '/*HAHM*/*/MINIAODSIM'                       Everything from one model, any campaign
./kamui find '/*Hto2Sto4D*/RunIII2024*/MINIAODSIM'        One signal family in one campaign
./kamui find '/*Stealth*/*/USER' --instance prod/phys03   Privately produced datasets
```

#### norm

Records the generator weight sum for normalization, in `config/normalizations/generatorSums.json`. The sums are read from the sample's central NanoAOD.
| Flag | Meaning |
| --- | --- |
| The five sample flags | |
| `--write` | Write results to the JSON |
| `--refresh` | Bypass the DAS cache |

```
./kamui norm --family tutorial            Report the sums, write nothing
./kamui norm --family tutorial --write    Record them
./kamui norm --tag validation --write     A whole tag at once
```

A sample whose dataset has no central NanoAOD is skipped. 

Use `./kamui check` to see how many catalogued samples have a sum recorded.

### Working with Registered Samples

#### list

Shows the samples in your config files, grouped by family. Four columns: the sample name, its era, the content preset it uses, and its tags.

| Flag | Meaning |
| --- | --- |
| `--datasets` | Print the bare DAS paths instead of the table |

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
| The five sample flags | |
| `--refresh` | Ignore the cache and ask DAS again |

```
./kamui query --tag validation                     The 24 Run 2 samples
./kamui query --family exoticHiggs4d2024           A whole family
./kamui query --tag rpv --refresh                  Ignore the cache
```

#### stage

Copies raw MiniAOD from the grid to our EOS area, for local tests. It copies the whole dataset unless `--maxFiles` caps it.

| Flag | Meaning |
| --- | --- |
| The five sample flags | |
| `--maxFiles N` | Cap on files copied |
| `--dryRun` | Print what would be copied, copy nothing |
| `--refresh` | Bypass the DAS cache |

```
./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024             One whole sample
./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024 --dryRun   Print what would be copied
./kamui stage --tag rpv --maxFiles 1                          One file each
```

#### cache

Describes the DAS cache, or thins it out. DAS is slow, so every answer is kept on disk and reused. Prints how many responses are held, how much space they take, how old they are, and how many have passed the 30 day age limit.
| Flag | Meaning |
| --- | --- |
| `--prune` | Delete expired entries |
| `--clear` | Delete every cached response |

```
./kamui cache                                      What is cached right now
./kamui cache --prune                              Drop the expired entries
./kamui cache --clear                              Throw the whole thing away
```

### Defining Our Ntuples

#### content

Shows what a content preset would write into your ntuples, without running anything. 

One row per collection: 

- Its name
- What kind of object it is
- Which MiniAOD collection it comes from
- How many variables are kept
- Any cut or cap.

| Flag | Meaning |
| --- | --- |
| `preset` | Optional. The preset or collection to resolve |
| `--data` | Resolve as data, which drops the `mcOnly` collections |
| `--era` | Era whose content set to resolve against (default `Summer24`) |
| `--write PATH` | Write the resolved JSON to this path |
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

| Flag | Meaning |
| --- | --- |
| The five sample flags | |
| `--task NAME` | Required. Names the directory under `ntupleProduction/jobs/` and the EOS output subdirectory |
| `--backend` | `condor` (default) or `crab` |
| `--content` | Override the content preset the selected samples uses |
| `--filesPerJob N` | Input files per job |
| `--maxFiles N` | Use at most this many input files per sample |
| `--memoryMB N` | Memory request per job (default 2500) |
| `--dryRun` | Write the job area, submit nothing |
| `--refresh` | Bypass the DAS cache |
| `--overwrite` | Overwrite an existing job area without asking |
| `--outputBase` | Write output under this EOS path instead of the site default |
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
| `--task NAME` | Required. A task under `ntupleProduction/jobs/` |

```
./kamui status --task run2Val
```

#### resubmit

Resubmits only the jobs of a task whose outputs never reached EOS. On CRAB it asks CRAB to retry its own failed jobs. On condor it compares what is on EOS against what the task expected.

| Flag | Meaning |
| --- | --- |
| `--task NAME` | Required. The task to retry |
| `--dryRun` | Report what would be resubmitted, submit nothing |
| `--forceResubmit` | Resubmit even while jobs from this task are still queued |
```
./kamui resubmit --task run2Val --dryRun           What is missing
./kamui resubmit --task run2Val                    Retry it
```

### Applying Selections

#### select

Applies an event-level selection to ntuples a `submit` task produced, and writes ntuples with the same branches.
| Flag | Meaning |
| --- | --- |
| The five sample flags | |
| `--selection NAME` | Required. A config in `config/selections/`, e.g. `run2Lepton` |
| `--task NAME` | Required. Names this selection pass |
| `--inputTask NAME` | Required. The ntuple production task to read from |
| `--inputBase` | EOS base holding the input ntuples (default: the site stageout base) |
| `--outputBase` | Where to write the selected ntuples |
| `--backend` | `local` (default) or `condor` |
| `--filesPerJob N` | Input files per job on condor (default 5) |
| `--dryRun` | Write the job area, submit nothing |

Output carries the same branches as input, so a selection can be applied to an earlier pass's output.
```
./kamui select --tag leptonTriggered --selection run2Lepton --task lepPass --inputTask run2Val                                 Run it locally
./kamui select --tag displacementTriggered --selection run2Displaced --task dispPass --inputTask run2Val --backend condor      Send it to the cluster
```

#### cutflow

Prints the cutflow a local `select` task recorded. Per cut, it quotes:

-  The events kept
- The events removed
- The step efficiency
- The cumulative efficiency.

| Flag | Meaning |
| --- | --- |
| `--task NAME` | Required. The select task |

```
./kamui cutflow --task lepPass
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
