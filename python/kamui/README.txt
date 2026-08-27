Kamui
=====

Kamui is the CLI for the whole analysis framework. Every stage of the analysis is meant to be driven through it, so there is one place to look for all of our analysis needs. It relies on a set of configuration files so we are never editing or hard-coding things into our scripts.

Sample processing is the only stage implemented so far, designed to turn CMS datasets into analysis ntuples on EOS.


Main Driver - cli.py
--------------------
Every command lives here, and running ./kamui goes straight to it. It reads what you asked for, hands the work to whichever part of the framework does it, and prints the result.

list
  - Shows the samples in your config files, grouped by family.
  - Four columns: the sample name, its era, the content preset it uses, and its tags. Add --datasets for the full DAS path.
  - Example commands:
      ./kamui list                                       Everything
      ./kamui list --name rpvStopDD_M400_ctau1mm_2018    One exact sample - repeat the flag for several samples
      ./kamui list --family rpv2024                      Everything in one single JSON config file
      ./kamui list --era 2018                            Everything in one era
      ./kamui list --tag validation                      One tag (a sample can carry several!)
      ./kamui list --match 'ggH-*ctau10mm*'              Glob on the sample name (quotes are necessary)
      ./kamui list --tag rpv --era 2018                  Combining different paths
      ./kamui list --tag validation --datasets           Return the bare DAS paths instead of the table

content
  - Shows what a preset would write into your ntuples, without running anything.
  - One row per collection: its name, what kind of object it is, which MiniAOD collection it comes from, how many variables are kept, and any cut or cap.
  - Example commands:
      ./kamui content                                    List the collections and presets available
      ./kamui content dvSignal                           What a preset resolves to, the default for MC
      ./kamui content dvFull                             Everything
      ./kamui content jets                               A single collection on its own
      ./kamui content dvSignal --data                    Resolved for data, the generator collections disappear
      ./kamui content dvRun2Lepton                       A Run 2 preset, note the trigger skim at the end
      ./kamui content dvFull --write resolved.json       Write out exactly what a job would be handed

query
  - Asks DAS how many files, events and gigabytes each selected sample holds, and totals them.
  - Needs cmsenv and a valid grid proxy. Answers are cached.
  - Example commands:
      ./kamui query --tag validation                     The 24 Run 2 samples, with a total at the bottom
      ./kamui query --family exoticHiggs4d2024           A whole family
      ./kamui query --match 'ggH-*'                      A glob
      ./kamui query --tag rpv --refresh                  Ignore the cache and ask DAS again

find
  - Searches DAS for datasets matching a wildcard, whether or not we have them in our configs.
  - Takes a pattern. Quote it, or the shell will try to expand it first.
  - Example commands:
      ./kamui find '/*HAHM*/*/MINIAODSIM'                       Everything from one model, any campaign
      ./kamui find '/*Hto2Sto4D*/RunIII2024*/MINIAODSIM'        One signal family in one campaign
      ./kamui find '/*Stealth*/*/USER' --instance prod/phys03   Privately produced datasets

stage
  - Copies raw MiniAOD from the grid to our EOS area.
  - It copies the whole dataset unless you pass --maxFiles N.
  - Files already on EOS are skipped.
  - Example commands:
      ./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024        One whole sample
      ./kamui stage --name ggH-2S-4D_mS55_ctau10mm_2024 --dry-run   Print what would be copied
      ./kamui stage --tag rpv --maxFiles 1                     One file each

submit
  - Produces the ntuples. It takes the samples you selected, works out what each job should write, builds a job area on disk, and sends it to CRAB or to condor.
  - --task names the production. It becomes the directory under ntupleProduction/jobs/ and the output subdirectory on EOS.
  - Always look at a --dry-run first. It writes the whole job area and submits nothing, so you can read the config files that would actually be used.
  - Task names are letters, digits, dot, dash and underscore, at most 96 characters, since the name becomes a directory, an EOS path and a shell word. Re-using one asks before it overwrites; overwriting deletes the old area, so the record of what was submitted is gone. Answer no and it writes to <task>_2 instead. --yes overwrites without asking, and with nothing attached to answer it always takes the safe branch. A task with a CRAB work area is never overwritten, since its jobs may still be running.
  - --filesPerJob wins when you pass it. Otherwise a sample's own unitsPerJob applies, and failing that, five. --maxFiles caps how many input files a sample uses at all.
  - Condor output goes to the shared lpcdisplacedvertices area and CRAB output to your own /store/user/<you>/Kamui, because CRAB will not write into another user's area. --outputBase sends either one somewhere else.
  - Example commands:
      ./kamui submit --tag validation --task run2Val --dry-run     Build the job area, submit nothing
      ./kamui submit --tag validation --task run2Val               The 24 Run 2 samples through CRAB
      ./kamui submit --name ggH-2S-4D_mS15_ctau1mm_2024 --task test --backend condor    One sample, run at LPC
      ./kamui submit --tag rpv --task rpvNtuples --content dvFull  Override the preset every sample uses
      ./kamui submit --tag signal --task withMini --output both    Write the slimmed MiniAOD alongside the ntuple
      ./kamui submit --tag rpv --task big --filesPerJob 10 --memoryMB 4000    Fewer, larger, hungrier jobs
      ./kamui submit --name ggH-2S-4D_mS15_ctau1mm_2024 --task quick --maxFiles 2    Two files only, for a fast test
      ./kamui submit --tag rpv --task elsewhere --outputBase /store/user/gdecastr/Scratch    Somewhere other than the default
      ./kamui submit --tag rpv --task big --yes                    Overwrite an existing job area without being asked

cache
  - Describes the DAS cache, or thins it out. DAS is slow, so every answer is kept on disk and reused.
  - Prints how many responses are held, how much space they take, how old they are, and how many have passed the 30 day age limit. Expired ones are ignored when read but sit on disk until removed.
  - --prune deletes only the expired entries. --clear deletes everything.
  - Example commands:
      ./kamui cache                                      What is cached right now
      ./kamui cache --prune                              Drop the expired entries, keep the rest
      ./kamui cache --clear                              Throw the whole thing away

status
  - Reports how a submitted task is doing. It reads the job area, sees which backend produced it, and asks that backend.
  - Example commands:
      ./kamui status --task run2Val                      Every CRAB project in the task

check
  - Validates every config file without touching the network.
  - It reads every sample and every content preset, resolves each preset for both MC and data, and complains about anything that does not add up.
  - Run it after editing any config, and before submitting anything. It exits non-zero when it finds a problem, so a script can rely on it.
  - Example commands:
      ./kamui check                                      Validate everything, print what it found

The Basics - foundations/
-------------------------
The bottom layer everything else is built on.

paths.py - Knows the paths where everything lives. It works this out from its own location, so there is nothing to set up and the framework runs wherever you check it out.

config.py - Reads the JSON config files.
- Any key starting with an underscore is treated as a comment and dropped, since JSON has no comment syntax.
- Config files inherit from each other like C++ classes.
  - Overriding a block replaces only the parts you name, so the settings originally defined survive.
  - Lists are the exception. There is no way to say "the base list plus mine", so restate anything you want to keep.


Reading the Configs - configReaders/
------------------------------------
Everything that turns a config file into something the code can use.

catalog.py - Reads the sample configs and answers "which samples do I mean". It expands grids into individual samples, then filters them by the selection flags you passed.

content.py - Reads the content presets and works out what a job should write. It flattens the include chain, drops the generator-level collections when the target is data, and turns the physics names you wrote into CMSSW-compatible language.

slimming.py - Works out the slimmed MiniAOD, when a job is asked for one. You name groups like jets or tracks in a preset, and this turns them into the list of EDM collections to keep.

sites.py - Reads sites.json, which says where things are stored and which CMSSW release to use. Paths in there are written with $USER, filled in when the file is read, so the framework works for whoever runs it.


Talking to the Grid - grid/
---------------------------
Everything that reaches outside our own machine.

das.py - Asks DAS what datasets and files exist. Answers are cached on disk.

fetch.py - Copies raw MiniAOD from the grid to our EOS area, for the stage command.


Submitting Jobs - submit/
-------------------------
Everything that turns a set of samples into running jobs. Each backend first writes a job area to disk and only then submits, so a --dry-run leaves you the exact files that would have been used.

A job area is one directory per task, under ntupleProduction/jobs/<task>/, holding everything a job needs.

common.py - The parts both backends share: making the task directory, flattening the content preset into it, splitting a file list into per-job groups, and writing task.json.

crab.py - The default backend. It writes one crabConfig per sample and submits them one at a time. CRAB sends each job to a site that already holds the data, splits the dataset itself, and retries failures on its own, so we never have to ask DAS which files exist.

condor.py - Runs at LPC instead, for when you want a fast answer on a handful of files: debugging a new preset, a private dataset CRAB is awkward about, or reprocessing what is already staged on our EOS. Because condor has no idea what a dataset is, this backend needs the file list up front, which is why submit asks DAS for it first. Jobs read their inputs over xrootd and copy the output back to EOS themselves. There are no automatic retries, and everything runs at FNAL no matter where the data lives, so a dataset with no copy here will read slowly. Use Rucio to replicate datasets if necessary.

Every task also writes a provenance record, task.json, and copies it to EOS next to the ntuples when the jobs are really submitted. It is meant to be read later by someone who has only the ROOT files: it carries the commit and branch the task was submitted from, whether that tree had uncommitted changes, who submitted it and when, the CMSSW release, the dataset and era behind every sample, and the fully resolved content.

What lands in a job area:
  task.json                      The provenance record described above, also copied to EOS
  <preset>.mc.json               The flattened content config, exactly as the cmsRun job receives it
  crabConfig_<sample>.py         CRAB only, one per sample
  fileLists.json                 Condor only, the input files each job gets
  jobList.txt                    Condor only, one row per job
  runJob_<preset>_<mc|data>.sh   Condor only, the script a worker runs
  submit.jdl                     Condor only, what condor_submit is given


Extras - helpers/
-----------------
Small things that are not part of the analysis.

banner.py - Draws the Sharingan when you run a command. Turn it off with --no-banner, which goes before the command, or set KAMUI_NO_BANNER=1 to never see it again.
