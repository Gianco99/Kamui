Content Configs
===============
These decide what ends up in your ntuples.

collections/ describes what a single kind of object is worth keeping: which variables of a jet, a muon, a track.
presets/ combines those into a complete job configuration. You write a preset to define a new production.

Run ./kamui content to list both, and ./kamui content <name> to see what any one of them resolves to.

Collections
-----------
A collection names one thing in MiniAOD and lists the variables to keep from it.

  type       What kind of object it is: patJet, patMuon, vertex, genParticle, etc..
  src        The MiniAOD collection it reads
  cut        Optional. Only objects passing this are kept
  maxLen     Optional. Keep at most this many, highest pT first
  mcOnly     Optional. The collection disappears when the preset is resolved for data
  variables  The branches to write

Each variable is a name and how to compute it:

  "pt": {"expr": "pt()", "type": "float", "doc": "corrected pT [GeV]", "precision": 10}

  expr        Any method of the underlying C++ object. Arithmetic and ?: conditionals work
  type        float, double, int, uint, int16, uint16, uint8 or bool
  doc         Written into the ROOT file as the branch description
  precision   Optional, floats only. How many bits of the mantissa to keep

precision is important; fewer bits means a smaller file, and 10 bits is roughly 0.1 percent.

Presets
-------
A preset is what you name when you submit. It says which collections to write, and optionally which events to keep.

  include    Other configs to build on, collections or presets
  skim       Optional. The trigger channel whose events to keep
  miniaod    Optional. Which groups to write into the slimmed MiniAOD, when a job is asked for one

Most presets are only an include list. A preset can also override anything it inherits.

What Is Here Now
----------------
  collections/core        Event level: PVs, beamspot, MET, rho, etc.
  collections/jets        AK4 PUPPI jets
  collections/leptons     Muons and electrons
  collections/vertices    Secondary vertices from MiniAOD
  collections/tracks      Tracks and lost tracks, the input to offline vertexing
  collections/gen         Generator particles, weights and PU (mcOnly)

  presets/dvBase          Adds leptons and vertices. Use for data
  presets/dvSignal        Adds generator information. The default for MC
  presets/dvFull          Adds tracks. Needed for offline vertexing, and much larger
  presets/dvRun2Displaced Run 2 validation, displacement-triggered channel
  presets/dvRun2Lepton    Run 2 validation, lepton-triggered channel

Run ./kamui check after editing anything here. It resolves every preset for both MC and data.
