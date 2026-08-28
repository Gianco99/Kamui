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

Six commands take the same five flags, and they combine: passing several narrows the set. `--name` may be repeated.

| Flag | What it matches |
| --- | --- |
| `--name` | Exact sample name, repeatable |
| `--family` | The sample config file, e.g. `exoticHiggs4d2024` |
| `--era` | Data-taking period: `2016`, `2016APV`, `2017`, `2018`, `Summer24` |
| `--tag` | A tag from the sample config, e.g. `validation`, `signal`, `leptonTriggered` |
| `--match` | Wildcard on the sample name; quote it or the shell eats it first |

The commands that take them are `list`, `query`, `stage`, `submit`, `select` and `norm`. Every one of them except `list` exits when nothing matched.


## Commands

### list

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
### content

Shows what a content preset would write into your ntuples, without running anything. One row per collection: its name, what kind of object it is, which MiniAOD collection it comes from, how many variables are kept, and any cut or cap. Naming no preset lists the presets each era set defines.

| Flag | Meaning |
| --- | --- |
| `preset` | Positional, optional. The preset or collection to resolve |
| `--data` | Resolve as data, which drops the `mcOnly` collections |
| `--era` | Era whose content set to resolve against (default `Summer24`) |
| `--write PATH` | Write the resolved JSON there, exactly as a job receives it |

An era reaches only its own content set, so a Run 2 preset needs `--era` to be a Run 2 year.

```
./kamui content                                    The presets run2 and run3 define
./kamui content dvSignal                           What a preset resolves to, for MC
./kamui content dvFull                             Everything
./kamui content jets                               A single collection on its own
./kamui content dvSignal --data                    The generator collections disappear
./kamui content dvLepton --era 2018                A Run 2 preset, note the trigger skim at the end
./kamui content dvFull --write resolved.json       Write out exactly what a job would be handed
```

### query

Asks DAS how many files, events and gigabytes each selected sample holds, and totals them. Needs cmsenv and a valid grid proxy. Answers are cached.

| Flag | Meaning |
| --- | --- |
| the five sample flags | |
| `--refresh` | Ignore the cache and ask DAS again |

```
./kamui query --tag validation                     The 24 Run 2 samples, with a total at the bottom
./kamui query --family exoticHiggs4d2024           A whole family
./kamui query --tag rpv --refresh                  Ignore the cache
```

### find

Searches DAS for datasets matching a wildcard, whether or not we have them in our configs.

| Flag | Meaning |
| --- | --- |
| `pattern` | Positional, required. Quote it |
| `--instance` | `prod/global` for official datasets (default), `prod/phys03` for USER ones |
| `--refresh` | Bypass the DAS cache |

```
./kamui find '/*HAHM*/*/MINIAODSIM'                       Everything from one model, any campaign
./kamui find '/*Hto2Sto4D*/RunIII2024*/MINIAODSIM'        One signal family in one campaign
./kamui find '/*Stealth*/*/USER' --instance prod/phys03   Privately produced datasets
```

### stage

Copies raw MiniAOD from the grid to our EOS area, for inspecting files and prototyping content presets. Files already on EOS are skipped. It copies the whole dataset unless `--maxFiles` caps it.

| Flag | Meaning |
| --- | --- |
| the five sample flags | |
| `--maxFiles N` | Hard cap on files copied |
| `--dryRun` | Print what would be copied, copy nothing |
| `--refresh` | Bypass the DAS cache |

```
./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024             One whole sample
./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024 --dryRun   Print what would be copied
./kamui stage --tag rpv --maxFiles 1                          One file each
```

### submit

Produces the ntuples. It takes the samples you selected, works out what each job should write, builds a job area on disk, and sends it to condor or to CRAB.

| Flag | Meaning |
| --- | --- |
| the five sample flags | |
| `--task NAME` | Required. Names the directory under `ntupleProduction/jobs/` and the EOS output subdirectory |
| `--backend` | `condor` (default) or `crab` for large productions |
| `--content` | Override the content preset every selected sample uses |
| `--output` | `ntuple` (default), `miniaod`, or `both` |
| `--filesPerJob N` | Input files per job |
| `--maxFiles N` | Use at most this many input files per sample |
| `--memoryMB N` | Memory request per job (default 2500) |
| `--dryRun` | Write the job area, submit nothing |
| `--refresh` | Bypass the DAS cache |
| `--yes` | Overwrite an existing job area without asking |
| `--outputBase` | Write output under this EOS path instead of the site default |

Always look at a `--dryRun` first. It writes the whole job area and submits nothing, so you can read the config files that would actually be used.

Task names are letters, digits, dot, dash and underscore, starting with a letter or digit, at most 96 characters, since the name becomes a directory, an EOS path and a shell word. Re-using one asks before it overwrites; overwriting deletes the old area, so the record of what was submitted is gone. Answer no and it writes to `<task>_2` instead. `--yes` overwrites without asking, and with nothing attached to answer it always takes the safe branch. A task with a CRAB work area is never overwritten, since its jobs may still be running.

`--filesPerJob` wins when you pass it. Otherwise a sample's own `unitsPerJob` applies, and failing that, five. `--maxFiles` caps how many input files a sample uses at all.

`--output miniaod` and `--output both` need the content preset to define a `miniaod` block, and submit refuses the task when it does not.

Condor output goes to the shared lpcdisplacedvertices area and CRAB output to your own `/store/user/<you>/Kamui`, because CRAB will not write into another user's area. `--outputBase` sends either one somewhere else.

```
./kamui submit --tag validation --task run2Val --dryRun                              Build the job area, submit nothing
./kamui submit --tag validation --task run2Val                                        The 24 Run 2 samples at LPC
./kamui submit --tag validation --task run2Val --backend crab                         The same, through CRAB
./kamui submit --tag rpv --task rpvNtuples --content dvFull                           Override the preset every sample uses
./kamui submit --tag signal --task withMini --output both                             Write the slimmed MiniAOD alongside the ntuple
./kamui submit --tag rpv --task big --filesPerJob 10 --memoryMB 4000                  Fewer, larger, hungrier jobs
./kamui submit --name ggH-2S-4D_mS15_ctau1mm_2024 --task quick --maxFiles 2           Two files only, for a fast test
./kamui submit --tag rpv --task elsewhere --outputBase /store/user/gdecastr/Scratch   Somewhere other than the default
```

### select

Applies an event-level selection to ntuples a `submit` task produced, and writes ntuples with the same branches. It prints, per sample, how many events went in and how many came out.

| Flag | Meaning |
| --- | --- |
| the five sample flags | |
| `--selection NAME` | Required. A config in `config/selections/`, e.g. `run2Lepton` |
| `--task NAME` | Required. Names this selection pass |
| `--inputTask NAME` | Required. The ntuple production task to read from |
| `--inputBase` | EOS base holding the input ntuples (default: the site stageout base) |
| `--outputBase` | Where to write the selected ntuples |
| `--cutflow` | Also write one ntuple per cut, for inspection. Local backend only |
| `--backend` | `local` (default) or `condor` |
| `--filesPerJob N` | Input files per job on condor (default 5) |
| `--dryRun` | Write the job area, submit nothing |

The selection is resolved once per era of the samples you picked, because thresholds, trigger lists and MET filter lists all depend on the year. A sample whose era the selection config does not list is an error.

Locally, the output and the cutflow land under `ntupleSelection/out/<task>/`. On condor, the job area is `ntupleSelection/jobs/<task>/` and each job copies its own ntuple and its own cutflow JSON to `<outputBase>/selected/<task>/<sample>/`.

```
./kamui select --tag leptonTriggered --selection run2Lepton --task lepPass --inputTask run2Val            Run it here, seconds for a small pass
./kamui select --tag leptonTriggered --selection run2Lepton --task lepPass --inputTask run2Val --cutflow  Keep one ntuple per cut
./kamui select --tag displacementTriggered --selection run2Displaced --task dispPass --inputTask run2Val --backend condor
```

### norm

Measures a sample's generator sums over a complete production and stores them in `config/crossSections/generatorSums.json`, which is the denominator every yield is normalized by. With no `--inputTask` it records the DAS event count alone, which is what you can do the moment a sample is added.

| Flag | Meaning |
| --- | --- |
| the five sample flags | |
| `--inputTask NAME` | A complete production task to measure the weight sum over |
| `--inputBase` | EOS base holding the ntuples (default: the site stageout base) |
| `--noDas` | Skip the DAS cross-check of the event count |

The measured event count is compared against DAS, and an entry that does not match is flagged INCOMPLETE. Do not normalize with one.

```
./kamui norm --tag validation                                  Record the DAS counts for the Run 2 samples
./kamui norm --tag validation --inputTask run2Val              Measure the weight sums over a finished production
./kamui norm --name rpvStopDD_M400_ctau1mm_2018 --noDas --inputTask run2Val
```

### cutflow

Prints the cutflow a local `select` task recorded: per cut, the events kept, the events removed, the step efficiency and the cumulative efficiency, with what each cut is and how it was applied. A task spanning several samples also gets a combined table.

| Flag | Meaning |
| --- | --- |
| `--task NAME` | Required. The select task |

```
./kamui cutflow --task lepPass
```

### status

Reports how a submitted production task is doing. It reads the job area, sees which backend produced it, and asks that backend.

| Flag | Meaning |
| --- | --- |
| `--task NAME` | Required. A task under `ntupleProduction/jobs/` |

```
./kamui status --task run2Val
```

### resubmit

Resubmits only the jobs of a task whose outputs never reached EOS. On CRAB it asks CRAB to retry its own failed jobs. On condor it compares what is on EOS against what the task expected, names the missing jobs, and submits a retry that writes to the same output directory, with its logs under `logs/retry<n>`.

| Flag | Meaning |
| --- | --- |
| `--task NAME` | Required. The task to retry |
| `--dryRun` | Report what would be resubmitted, submit nothing |
| `--yes` | Resubmit even while jobs from this task are still queued |

A job still on the queue has not failed, so resubmitting while any are running would write the same output twice. It refuses unless you pass `--yes`.

```
./kamui resubmit --task run2Val --dryRun          What is missing
./kamui resubmit --task run2Val                    Retry it
```

### check

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

### cache

Describes the DAS cache, or thins it out. DAS is slow, so every answer is kept on disk and reused. Prints how many responses are held, how much space they take, how old they are, and how many have passed the 30 day age limit. Expired entries are ignored when read but sit on disk until removed.

| Flag | Meaning |
| --- | --- |
| `--prune` | Delete only the expired entries, keeping the rest |
| `--clear` | Delete every cached response |

```
./kamui cache                                      What is cached right now
./kamui cache --prune                              Drop the expired entries
./kamui cache --clear                              Throw the whole thing away
```


## The Basics - foundations/

The bottom layer everything else is built on.

`paths.py` - Knows the paths where everything lives. It works this out from its own location, so there is nothing to set up and the framework runs wherever you check it out.

`config.py` - Reads the JSON config files.
- Any key starting with an underscore is treated as a comment and dropped, since JSON has no comment syntax.
- Config files inherit from each other like C++ classes. Overriding a block replaces only the parts you name, so the settings originally defined survive.
- Lists are the exception. There is no way to say "the base list plus mine", so restate anything you want to keep.


## Reading the Configs - configReaders/

Everything that turns a config file into something the code can use.

`catalog.py` - Reads the sample configs and answers "which samples do I mean". It expands grids into individual samples, then filters them by the selection flags you passed.

`content.py` - Reads the content presets and works out what a job should write. It flattens the include chain, drops the generator-level collections when the target is data, and turns the physics names you wrote into CMSSW-compatible language. It also reads the trigger configs, which is where a skim's HLT path list comes from.

`selections.py` - Reads the selection configs that drive `select`. It flattens the include chain, checks every key, cut type and quantity name, and resolves each era-dependent threshold, trigger list and flag list down to a single value for the era you asked for. What comes out is self-contained, so a worker never opens a config directory.

`sites.py` - Reads `sites.json`, which says where things are stored and which CMSSW release to use. Paths in there are written with `$USER`, filled in when the file is read, so the framework works for whoever runs it.


## Talking to the Grid - grid/

Everything that reaches outside our own machine.

`das.py` - Asks DAS what datasets and files exist. Answers are cached on disk.

`fetch.py` - Copies raw MiniAOD from the grid to our EOS area, for the `stage` command.


## Submitting Jobs - submit/

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


## Selecting Events - select/

Everything behind the `select`, `cutflow` and `norm` commands. Inputs are the ntuples a production task wrote; outputs are ntuples with the same branches, plus a cutflow.

`engine.py` - Applies a resolved selection. It reads the input ntuples with uproot, builds one mask per cut in the order the config lists them, writes the surviving events, and returns the cutflow. It knows six kinds of cut: `trigger`, `object`, `flags`, `quantity`, `veto` and `anyOf`. Any cut can carry `invert`, which keeps exactly the events it would otherwise have thrown away. It also computes the per-track impact parameters and the jet identification, which the ntuples store as raw ingredients rather than finished quantities.

`quantities.py` - The event-level quantities a selection config may name, each with the branches it needs and a one-line description. `HT40`, `caloHT30`, `nJet40`, `leadMuonPt` and `MET` are among them, and the TightLepVeto jet identification the jet-based ones apply lives here too.

`io.py` - Finds the input ntuples for a sample inside a production task, over xrootd or on a local disk, and writes and prints the cutflow.

`batch.py` - Builds the condor job area for a selection pass under `ntupleSelection/jobs/<task>/`, packages the kamui source so a worker can import it, and submits.

`runOne.py` - What a worker runs: `python3 -m kamui.select.runOne <selectionJson> <outputFile> <input> [input ...]`. It applies the already-resolved selection to one group of files and writes the cutflow beside the output.

`normalization.py` - The generator sums a sample must be normalized by. It sums the run-level counters over a complete production, records them against the DAS event count, and refuses to hand back a denominator measured over an incomplete one.


## Extras - helpers/

Small things that are not part of the analysis.

`banner.py` - Draws the Sharingan when you run a command. Turn it off with `--noBanner`, which goes before the command, or set `KAMUI_NO_BANNER=1` to never see it again.
