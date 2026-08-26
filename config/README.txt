Config
======
Everything the framework reads is here. Three subjects, three places.

  samples/    Which datasets to process
  content/    Which quantities to write out
  triggers/   Which HLT paths define a channel
  sites.json  Where things are stored and which CMSSW release to use

Each subdirectory has its own README. This file covers sites.json.

sites.json
----------
The one place a storage path, a redirector or a release version is written down.

  eosRedirector      The xrootd door for our EOS area
  sourceRedirector   The xrootd door for reading datasets off the grid
  stageoutBase       Where output is written, both raw copies and job output
  miniaodDir         The subdirectory under stageoutBase holding raw MiniAOD copies
  crabStorageSite    The site CRAB is told to deliver to
  cmssw.version      The CMSSW release jobs run in
  cmssw.scramArch    The architecture that release was built for

Paths use $USER rather than a name, and it is filled in when the file is read.

The CMSSW version is pinned on purpose. Bumping it here is a one-line change and the condor jobs follow automatically, but do not do it unless absolutely necessary since a release change can introduce errors across the whole repository.
