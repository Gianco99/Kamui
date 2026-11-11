# Config

This folder holds every configuration file the framework reads. Each kind of config except `sites.json` sits in its own subfolder, and each subfolder has its own README.

| Path | What it holds |
|---|---|
| `samples/` | Which datasets to process |
| `content/` | Collections, which describe sets of physics objects, and presets, which combine them into what we want to include in ntuples |
| `triggers/` | The HLT paths we impose |
| `selections/` | The ordered event-level cuts |
| `definitions/` | Named lists of cuts, such as the jet ID, that you write once and reuse in selections and content configs |
| `normalizations/` | Cross sections, luminosities, and per-sample generator weight sums, to normalize yields |
| `sites.json` | Storage paths, redirectors, CRAB site, CMSSW release |

Samples, triggers, selections and definitions keep one folder per run, `run2/` and `run3/`, as `content/` does. A sample's era decides which run folder each of its configs comes from, so the same file name can exist for both runs and a file name never carries the run. For example, a 2018 sample that asks for the `lepton` selection gets `selections/run2/lepton.json`.

## sites.json

A single file with the settings for CMSSW, EOS, condor and CRAB.

| Key | Meaning |
|---|---|
| **`eosRedirector`** (required) | The xrootd address of our EOS area |
| **`sourceRedirector`** (required) | The xrootd address for reading datasets from the grid |
| **`stageoutBase`** (required) | Where condor outputs are written |
| **`crabStageoutBase`** (required) | Where CRAB outputs are written |
| **`miniaodDir`** (required) | The subdirectory under `stageoutBase` where `stage` copies MiniAOD files |
| **`crabStorageSite`** (required) | The site CRAB is told to deliver to |
| **`globalTags`** (required) | The conditions tag per era, as `mc` and `data` |
| **`cmssw.version`** (required) | The CMSSW release jobs run in |
| **`cmssw.scramArch`** (required) | The architecture that release was built for |

The paths use `$USER`, which Kamui fills in when it reads the file.

For datasets already cached at FNAL, `root://cmsxrootd.fnal.gov/` is a faster `sourceRedirector`.

## Caveats

- `_doc` is the only comment key. Write at most one per object: one plain sentence on what that object is for. Kamui removes it when it reads the file, at any depth.
- `doc`, without the underscore, is text Kamui writes into its outputs, such as an ntuple branch description or a cutflow row.
- Keep the layout compact: short objects and lists sit on one line, and long lists put one item per line. `normalizations/generatorSums.json` keeps its own layout, since `./kamui norm --write` rewrites it.
- `include` is a list of config names to pull in. Each included config loads its own includes first, and nested blocks merge key by key. An include loop is an error.
- Only JSON objects merge. A list or single value replaces the included one, so a config that names a list throws away the included list entirely.
- To find a config named `<name>`, Kamui looks for `<name>.json` in the run folder of the era being run, and in each subfolder one level below it. A name found in two of those folders is an error unless you write it with its subfolder, such as `presets/<name>`.
- Only code in `configReaders/` may open these files.
  - `select/normalization.py` is an exception.
- CRAB refuses to write under another user's `/store/user` area, so it can't use the shared `lpcdisplacedvertices` directory and gets its own `crabStageoutBase`. Condor copies its outputs with `xrdcp` and has no such restriction, so it writes to the shared group area.
