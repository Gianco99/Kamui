# Config

This folder holds all the configuration files the framework reads. Each subdirectory has its own documentation.

| Path | What it holds |
|---|---|
| `samples/` | Which datasets to process. |
| `content/` | Collections describe sets of physics objects. Presets combine them into what we want to include in ntuples. |
| `triggers/` | The HLT paths we impose. |
| `selections/` | The ordered event-level cuts. |
| `definitions/` | Named lists of cuts, such as the jet ID, that you write once and reuse in selections and content configs. |
| `normalizations/` | Cross sections, luminosities, and per-sample generator weight sums to normalize yields. |
| `sites.json` | Storage paths, redirectors, CRAB site, CMSSW release. |

Samples, triggers, selections and definitions keep one folder per run, `run2/` and `run3/`, the way `content/` does. A sample's era decides which run folder each of its configs comes from, so the same file name can exist for both runs and never carries the run itself.
## sites.json

Standalone file containing the configuration for CMSSW, EOS, Condor and CRAB.

| Key | Meaning |
|---|---|
| `eosRedirector` | The xrootd address of our EOS area |
| `sourceRedirector` | The xrootd address for reading datasets from the grid |
| `stageoutBase` | Where Condor outputs are written |
| `crabStageoutBase` | Where CRAB outputs are written |
| `miniaodDir` | The subdirectory under `stageoutBase` where `stage` copies MiniAOD files |
| `crabStorageSite` | The site CRAB is told to deliver to |
| `globalTags` | The conditions tag per era, as `mc` and `data` |
| `cmssw.version` | The CMSSW release jobs run in |
| `cmssw.scramArch` | The architecture that release was built for |

Paths use `$USER`, filled in when the file is read.

For datasets already cached at FNAL, `root://cmsxrootd.fnal.gov/` is a faster `sourceRedirector`.

## Caveats

- `_doc` is the only comment key: at most one per object, one plain sentence on what that object is for. Kamui removes it when it reads the file, at any depth.
- `doc` is different: it is text Kamui writes out, such as an ntuple branch description or a cutflow row.
- The files use a compact layout: short objects and lists sit on one line, and long lists put one item per line. `normalizations/generatorSums.json` keeps its own layout, since `./kamui norm --write` rewrites it.
- `include` pulls in other configs, each with its own includes loaded first, and merges nested blocks key by key. An include loop is an error.
- Only JSON objects merge. Lists and single values replace the included ones, so a config that names a list throws away the included list entirely.
- To find a config named `<name>`, Kamui looks for `<name>.json` in the folder for that kind of config first, then in each subfolder one level below it, in alphabetical order.
- Only code in `configReaders/` may open these files, and `./kamui check` fails if any other code in `python/kamui/` does.
  - `select/normalization.py` is an exception.
- CRAB refuses to write under another user's `/store/user` area, so it cannot use the shared `lpcdisplacedvertices` directory and has its own `crabStageoutBase`.
- Condor copies its outputs with `xrdcp` and has no such restriction, so it writes to the shared group area.
