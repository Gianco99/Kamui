# Config

Everything the framework reads is here. A subdirectory per subject, each with its own README, plus two standalone JSON files documented below.

| Path | What it holds |
|---|---|
| `samples/` | Which datasets to process, one JSON file per sample family. See `samples/README.md`. |
| `content/` | Which quantities to write out: collections describing one kind of object, presets combining them into a production. Split into `run2/` and `run3/`. See `content/README.md`. |
| `triggers/` | Which HLT paths define a channel. See `triggers/README.md`. |
| `selections/` | The ordered event-level cuts `./kamui select` applies to production ntuples. See `selections/README.md`. |
| `crossSections/` | Cross sections and the per-sample generator sums a yield is normalized by. See `crossSections/README.md`. |
| `sites.json` | Storage paths, redirectors, CRAB site, CMSSW release. |
| `lumi.json` | Integrated luminosity per era and per channel. |

## sites.json

The one place a storage path, a redirector or a release version is written down.

| Key | Meaning |
|---|---|
| `eosRedirector` | The xrootd door for our EOS area |
| `sourceRedirector` | The xrootd door for reading datasets off the grid |
| `stageoutBase` | Where condor output is written, both raw copies and job output |
| `crabStageoutBase` | The same for CRAB, which needs its own area |
| `miniaodDir` | The subdirectory under `stageoutBase` holding raw MiniAOD copies |
| `crabStorageSite` | The site CRAB is told to deliver to |
| `cmssw.version` | The CMSSW release jobs run in |
| `cmssw.scramArch` | The architecture that release was built for |

Paths use `$USER`, filled in when the file is read.

The CMSSW version is pinned on purpose. Bumping it here is a one-line change and the condor jobs follow automatically, but do not do it unless absolutely necessary since a release change can introduce errors across the whole repository.

## lumi.json

Integrated luminosity in inverse picobarns, and the record of where each number came from. It is the `lumi` term of the yield formula written out in `crossSections/README.md`.

`eras` is keyed by CMS MC campaign name and covers `2016APV`, `2016`, `2017`, `2018`, `Summer22`, `Summer22EE`, `Summer23`, `Summer23BPix` and `Summer24`. Each entry carries a `lumi` and a `source` naming the golden JSON and normtag the value was integrated over, so a number can be re-derived when either changes.

`channels` overrides an era value where a trigger was not live for the whole run. The b-jet triggers came late in 2017 and 2018, so `channels.displaced` gives that channel less luminosity than the era total; normalize the displacement-triggered channel with the channel number.
