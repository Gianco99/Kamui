# Kamui CLI

Kamui is the CLI for the whole analysis framework. Every stage of the analysis is meant to run through it, so there is one place to look for everything. It reads what to do from the configuration files, so nothing is edited or hard-coded into the scripts.

These terms come up throughout:

- A sample is one dataset registered in a file under `config/samples/`, with a name, an era and tags.
- A content preset says which collections, such as jets or tracks, and which of their variables a sample's ntuples keep. Each sample names its preset.
- A task is one run of `submit` (a production task) or `select` (a selection pass), named with `--task`. A production task or a condor selection pass builds its jobs in a folder of that name, the job area, and its output lands in another folder of that name. A local pass writes only to `ntupleSelection/out/<task>/`.

Every command has the same shape:

```
./kamui <command> [flags]
```

For example, `./kamui list --tag validation` shows every sample tagged `validation`, and `./kamui <command> --help` prints one command's flags.

## Picking Samples

Six commands pick their samples with the same five flags: `list`, `query`, `stage`, `submit`, `select` and `norm`.

| Flag | What it matches |
| --- | --- |
| `--name NAME` (optional) | Exact sample name. Repeat the flag to name several |
| `--family NAME` (optional) | The `family` key of a file in `config/samples/`, or the file's name when it has no `family` key |
| `--era NAME` (optional) | Data-taking period |
| `--tag NAME` (optional) | A tag from the sample config |
| `--match PATTERN` (optional) | Wildcard on the sample name |

A sample has to match every flag you give.

## Commands

### Initial Framework Setup

#### check

Validates the config files locally, reporting on each check:

| Check | What it means |
| --- | --- |
| Catalog | Every sample is listed once and well formatted |
| Content | Every preset and collection file resolves for each era of its run, as MC and as data, and every sample's preset exists in its run |
| Parked content | Warns about the content files `check` skips while their configuration is unfinished |
| Selections | Every selection resolves for each era it declares, or for each era of its run when it declares none |
| Definitions | The common definitions, shared to avoid repeating the same cuts, are valid for each era |
| Triggers | Every trigger file is well formatted |
| Normalizations | Every JSON file in `config/normalizations/` is well formatted |
| Generator sums | How many MC samples know their total generator weight. A missing one only warns, with a reminder to run `./kamui norm --write` |
| Sites and CMSSW | `sites.json` and the CMSSW job script configurations are valid |

Each line starts with a check mark when it passes, a cross for a failure or a warning sign for something incomplete. `check` exits non-zero on any failure, and a warning alone does not fail it. Run it after editing any config and before submitting anything.

```
./kamui check
```

### Registering a Sample

#### find

Searches DAS for datasets matching a wildcard, whether or not our configs have them. It needs cmsenv and a valid grid proxy.

| Flag | Meaning |
| --- | --- |
| **`pattern`** (required) | Positional. The DAS wildcard |
| `--instance INSTANCE` (optional, default `prod/global`) | `prod/global` for central datasets, `prod/phys03` for USER ones |
| `--refresh` (optional) | Bypass the DAS cache |

```
./kamui find '/*HAHM*/*/MINIAODSIM'                       Everything from one model, any campaign
./kamui find '/*Hto2Sto4D*/RunIII2024*/MINIAODSIM'        One signal family in one campaign
./kamui find '/*Stealth*/*/USER' --instance prod/phys03   Privately produced datasets
```

#### norm

Measures each MC sample's generator weight sum, which normalization needs, from its central NanoAOD, and with `--write` records it in `config/normalizations/generatorSums.json`. It skips data samples, which have no generator weights, and any sample whose dataset has no central NanoAOD.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See Picking Samples |
| `--write` (optional) | Write the sums to the JSON |
| `--refresh` (optional) | Bypass the DAS cache |

```
./kamui norm --family tutorial            Report the sums, write nothing
./kamui norm --family tutorial --write    Record them
./kamui norm --tag validation --write     A whole tag at once
```

### Working with Registered Samples

#### list

Shows the samples in your config files, grouped by family, in four columns:

- The sample name
- The era
- The content preset it uses
- Its tags

| Flag | Meaning |
| --- | --- |
| The five sample flags | See Picking Samples |
| `--datasets` (optional) | Print only the bare DAS paths |

```
./kamui list                                       Everything
./kamui list --name rpvStopDD_M400_ctau1mm_2018    One exact sample
./kamui list --family rpv2024                      Everything in one sample config file
./kamui list --era 2018                            Everything in one era
./kamui list --tag validation                      One tag (a sample can carry several!)
./kamui list --match 'ggH-*ctau10mm*'              Wildcard on the sample name
./kamui list --tag rpv --era 2018                  Combining flags
./kamui list --tag validation --datasets           Just the DAS paths
```

#### query

Asks DAS how many files, events and gigabytes each selected sample holds, and adds up the totals. It needs cmsenv and a valid grid proxy.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See Picking Samples |
| `--refresh` (optional) | Ignore the cache and ask DAS again |

```
./kamui query --tag validation                     Every sample tagged validation
./kamui query --family exoticHiggs4d2024           A whole family
./kamui query --tag rpv --refresh                  Ignore the cache
```

#### stage

Copies a sample's MiniAOD files to EOS, into `<stageoutBase>/<miniaodDir>/<sample>/` with `stageoutBase` and `miniaodDir` from `config/sites.json`, to run one job by hand on files at FNAL (see Running One Job by Hand in `ntupleProduction/README.md`) or to prototype a content preset. Without `--maxFiles` it copies the whole dataset.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See Picking Samples |
| `--maxFiles N` (optional) | Copy at most this many files per sample |
| `--dryRun` (optional) | Print what would be copied, and copy nothing |
| `--refresh` (optional) | Bypass the DAS cache |

```
./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024             One whole sample
./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024 --dryRun    Print what would be copied
./kamui stage --tag rpv --maxFiles 1                          One file each
```

### Defining Our Ntuples

#### content

Shows what a content preset would write into your ntuples, without running anything. `config/content/README.md` explains how to write a collection or preset.

It prints a table with one row per collection, showing:

- Its name
- What kind of object it is
- The MiniAOD collection it comes from
- How many variables it keeps
- Any cut or cap

Then it lists each collection's branches: `n<Collection>` when it has many entries per event, and `<Collection>_<variable>` for each variable.

| Flag | Meaning |
| --- | --- |
| `preset` (optional) | Positional. The preset or collection to show. Leave it out to list the presets |
| `--data` (optional) | Show the data version, which drops the `mcOnly` collections |
| `--era NAME` (optional, default `Summer24`) | Picks the Run 2 or Run 3 content files and any per-era values |
| `--write PATH` (optional) | Write the JSON a job would receive to this path |

```
./kamui content                                    The presets run2 and run3 define
./kamui content dvSignal                           What one preset would write
./kamui content jets                               A single collection on its own
./kamui content dvSignal --data                    The generator collections disappear
./kamui content dvLepton --era 2018                A Run 2 preset
./kamui content dvFull --write resolved.json       Exactly what a job would be handed
```

### Producing the Ntuples

These commands run job submission, which `ntupleProduction/README.md` explains in detail.

#### submit

Produces the ntuples: it works out what each job writes, builds a job area, and sends it to condor or CRAB.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See Picking Samples |
| **`--task NAME`** (required) | Names the folder under `ntupleProduction/jobs/` and the EOS output subfolder |
| `--backend BACKEND` (optional, default `condor`) | `condor` or `crab` |
| `--content NAME` (optional) | Content preset for every selected sample, overriding their own |
| `--filesPerJob N` (optional) | Input files per job. Defaults to the sample's `unitsPerJob`, or `5` when it has none |
| `--maxFiles N` (optional) | Use at most this many input files per sample |
| `--memoryMB N` (optional, default `2500`) | Memory per job, in MB |
| `--dryRun` (optional) | Write the job area, and submit nothing |
| `--refresh` (optional) | Bypass the DAS cache |
| `--outputBase PATH` (optional) | Write the output under this EOS path. Defaults to the backend's base in `sites.json` |

```
./kamui submit --tag validation --task run2Val --dryRun                               Build the job area, submit nothing
./kamui submit --tag validation --task run2Val --backend crab                         Every sample tagged validation, through CRAB
./kamui submit --tag rpv --task rpvNtuples --content dvFull                           Override the preset every sample uses
./kamui submit --tag rpv --task big --filesPerJob 10 --memoryMB 4000                  Fewer, larger, hungrier jobs
./kamui submit --name ggH-2S-4D_mS15_ctau1mm_2024 --task quick --maxFiles 2           Two files only, for a fast test
./kamui submit --tag rpv --task elsewhere --outputBase /store/user/gdecastr/Scratch   Output somewhere other than the default
```

#### status

Reports how a production task or a condor selection pass is doing. It reads the job area to learn whether condor or CRAB ran the task, and asks that backend.

- On condor it shows the jobs of the first submission and of every retry, then `Outputs N/M present on EOS`.
- On CRAB it also names any sample whose crab submit failed.

| Flag | Meaning |
| --- | --- |
| **`--task NAME`** (required) | A task under `ntupleProduction/jobs/` or `ntupleSelection/jobs/` |

```
./kamui status --task run2Val
```

#### resubmit

Resubmits only the jobs of a production task whose outputs never reached EOS. On CRAB it asks CRAB to retry its own failed jobs, and submits again any sample whose crab submit failed.

| Flag | Meaning |
| --- | --- |
| **`--task NAME`** (required) | The production task to retry |
| `--memoryMB N` (optional) | Memory per retried job, in MB. Without it, each asks for what the task's submit asked for |
| `--dryRun` (optional) | Report what would be resubmitted, and submit nothing |
| `--forceResubmit` (optional) | Resubmit even while jobs from this task may still be queued or held |

```
./kamui resubmit --task run2Val --dryRun           What is missing
./kamui resubmit --task run2Val                    Retry it
./kamui resubmit --task run2Val --memoryMB 6000    Retry with more memory, for jobs held for exceeding their memory request
```

### Applying Selections

#### selection

With no name, lists each run's selections and the eras each declares. With a name and an `--era`, prints the selection exactly as `select` applies it for that era, with every definition expanded and every era-keyed threshold filled in.

| Flag | Meaning |
| --- | --- |
| `selection` (optional) | Positional. A selection name, or several joined by commas. Leave it out to list the selections |
| `--era NAME` (optional) | The era to resolve for, which picks the run folder and every era-keyed threshold. Needed with a name |
| `--write PATH` (optional) | Write the resolved JSON to this path instead of printing it |

```
./kamui selection                                  Every selection, by run
./kamui selection lepton,dv3x4 --era 2018          A stack, as select would apply it
```

#### select

Applies an event-level selection to the ntuples a `submit` task produced, and writes ntuples with the same branches. `config/selections/README.md` explains how to write a cut.

| Flag | Meaning |
| --- | --- |
| The five sample flags | See Picking Samples |
| **`--selection NAME`** (required) | A config in `config/selections/`, read from the run folder of the samples' era. Several joined by commas, such as `lepton,dv3x4`, apply in that order in one go. A selection with `blind` set to `true` never runs on data (see `blind` in `config/selections/README.md`) |
| **`--task NAME`** (required) | Names this selection pass, which must differ from every production task name |
| **`--inputTask NAME`** (required) | The ntuple production task to read from |
| `--inputBase PATH` (optional) | The base holding `<base>/ntuples/<inputTask>`, on EOS or local. Defaults to the output directory in the `task.json` of the input task's local job area, else `stageoutBase` in `sites.json` |
| `--outputBase PATH` (optional) | The EOS base for the selected ntuples, condor only. Defaults to `stageoutBase` in `sites.json` |
| `--backend BACKEND` (optional, default `local`) | `local` or `condor` |
| `--filesPerJob N` (optional, default `5`) | Input files per job on condor |
| `--memoryMB N` (optional, default `2000`) | Memory per job on condor, in MB |
| `--maxFiles N` (optional) | Use at most this many input files per sample |
| `--dryRun` (optional) | Locally, print each sample's input file count, output path and resolved selection, and run nothing. On condor, write the job area and submit nothing |

The output depends on the backend:

- A local pass writes `<sample>/<sample>_selected.root`, `cutflow.json` and `task.json` under `ntupleSelection/out/<task>/`.
- A condor pass builds its job area in `ntupleSelection/jobs/<task>/`, writes to `<base>/selected/<task>/` on EOS, and copies `task.json` there.

Either way, `task.json` records the input task, the selection resolved for each era, and the commit that ran.

```
./kamui select --tag leptonTriggered --selection lepton --task lepPass --inputTask run2Val                                     Run it locally
./kamui select --tag displacementTriggered --selection displaced --task dispPass --inputTask run2Val --backend condor          Send it to the cluster
./kamui select --tag leptonTriggered --selection lepton --task lepTest --inputTask run2Val --maxFiles 1 --dryRun               See what a pass would read, write and apply
```

#### cutflow

Prints the cutflow a `select` task recorded, local or condor. For a condor pass it adds up the cutflow each job left on EOS, and until every job has reported, it says how many jobs the counts cover. For each cut it shows:

- The events kept
- The events removed
- The step efficiency
- The cumulative efficiency

The first row is `generated`, the events in the whole dataset as `norm` recorded them. A sample without a recorded sum, or whose production or this pass read only part of the dataset with `--maxFiles`, starts instead at `input`, the events in the ntuples.

| Flag | Meaning |
| --- | --- |
| **`--task NAME`** (required) | A select task, local or condor |

```
./kamui cutflow --task lepPass
```

### DAS Cache

#### cache

DAS is slow, so `find`, `query`, `stage`, `norm` and `submit` keep every DAS answer on disk and reuse it. `cache` prints how many answers are stored, their size and age, and how many have expired, and can thin them out. An answer expires once older than `CACHE_MAX_AGE_DAYS` in `grid/das.py`, and the next command that needs it asks DAS again.

| Flag | Meaning |
| --- | --- |
| `--prune` (optional) | Delete the expired entries |
| `--clear` (optional) | Delete every cached response |

```
./kamui cache                                      What is cached right now
./kamui cache --prune                              Drop the expired entries
./kamui cache --clear                              Throw the whole thing away
```

## The Code Behind It

`cli.py` is a thin driver, and these folders hold the modules it calls:

| Folder | What it does |
| --- | --- |
| `foundations/` | The bottom layer: where each file lives, and how a JSON config file is read |
| `configReaders/` | The only folder that opens config files |
| `grid/` | Everything that reaches outside our own machine |
| `submit/` | Building and sending job areas |
| `select/` | Applying a selection to ntuples |
| `helpers/` | Extras |

## Caveats

- Keep the physics in the configuration files. This code only carries out what they say.
- A new analysis stage belongs here, as new commands.
- Keep `cli.py` thin: it parses the command line, calls a module, and prints. Put the behavior in the modules, so they can be imported without the CLI.
- `--help` lists the commands in the order `cli.py` adds them. Keep that order the same as this README's.
