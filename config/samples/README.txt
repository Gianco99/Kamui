Sample Configs
==============
One JSON file per sample family. Each file declares a set of datasets to process, and everything in it becomes selectable from the command line.

Fields
------
Every sample ends up with these, while anything else is rejected on load.

  name           Our short handle for the sample; must be unique across all families. Also serves as the EOS output subdirectory.
  dataset        The full DAS dataset path.
  dasInstance    prod/global for central datasets. prod/phys03 for USER-created ones.
  isMC           True for simulation. False for data.
  era            Summer24, Summer23, 2018, 2016APV, etc..
  family         The JSON file this sample came from. Filled in automatically.
  content        Which content preset defines the branches to write, e.g. dvSignal
  tags           Free-form labels, used for selection.
  nFilesFor10k   Files needed for roughly 10k events. Used only by stage and by submit --backend condor --quick; production submissions ignore it.
  unitsPerJob    Overrides the job splitting for this sample
  lumiMask       Data only.
  notes          Anything a reader would want to know

Family and tag are the two ways to select a group of samples.
  Family tells you which JSON file the sample is written in, and every sample has exactly one.
  Tag tells you what the sample is for, and a sample can carry several.

Writing a JSON File
-------------------
A family lists samples one of two ways.
  Explicitly, when there are only a few, under a "samples" key.
  As a grid, when the datasets follow a pattern, under a "grids" key.

A grid is a name template, a dataset template, and a list of axes. Every combination of the axes is generated, and each one fills in the {placeholders}. Two masses and four eras give eight samples:
  "name":    "rpvStopDD_M{mass}_ctau1mm_{era}",
  "dataset": "/StopStopbarTo2Dbar2D_M-{mass}_CTau-1mm_.../{campaign}/MINIAODSIM",
  "axes": {
    "mass": ["400", "600"],
    "era":  [{"era": "2016APV", "campaign": "RunIISummer20UL16MiniAODAPVv2-..."}, ...]
  }
Notice the two axes are written differently. Write an axis as a plain list when each value fills in one placeholder of the same name, as mass does. Write it as a list of blocks when picking one value has to fill in several placeholders at once, as era does.

"defaults" applies to every sample in the file.
"overrides" applies last, keyed by the final sample name, and is where per-point exceptions go such as a measured nFilesFor10k.
Keys beginning with an underscore are comments and are stripped on load, so you can annotate them freely.

Run ./kamui check after editing anything here. It validates every file to make sure it follows the appropriate convention.

Catalog
-------
  exoticHiggs4d2024    Summer24 Exotic Higgs - Central
  stealthSusy2024      Summer24 Stealth SUSY SHH and SYY - Private
  rpv2024              Summer24 RPV stop to dd - Private
  run2Validation       Run 2 UL points for replicating JMTucker results - Central
