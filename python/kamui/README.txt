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


Extras - helpers/
-----------------
Small things that are not part of the analysis.

banner.py - Draws the Sharingan when you run a command. Turn it off with --no-banner, or set KAMUI_NO_BANNER=1 to never see it again.
