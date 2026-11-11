# Grid

This folder holds everything that reaches outside our own machine. The datasets we analyze live on the grid, the network of computing sites that store CMS data. DAS is the catalog of those datasets and their files. For example, `./kamui query --family <family>` asks DAS, through `das.py`, how many files, events and GB each sample holds.

`das.py`: Asks DAS what datasets and files exist, and caches every answer on disk. It also finds a sample's central NanoAOD, the officially produced NanoAOD of the same dataset, because `norm` reads the generator weight sum from it.

`fetch.py`: Copies a sample's MiniAOD files from the grid to EOS, under `<stageoutBase>/<miniaodDir>/<sample>/`.

Both need `cmsenv` and a valid grid proxy.

## Caveats

- A DAS call with no cached answer needs a grid proxy that is not about to expire. Cached answers work without a proxy.
- `das.py`
    - Answers are cached under `ntupleProduction/.dasCache/` and go stale after `CACHE_MAX_AGE_DAYS`.
    - An empty answer that came with a dasgoclient warning is returned without being cached.
    - DAS answers a name it does not know with a summary of zeros and null dates, so Kamui counts a dataset as found only if its summary has a date or at least one file.
    - If several NanoAOD versions match, the last in string order wins, so `NanoAODv9` is picked over `NanoAODv12`.
- `fetch.py`
    - A file already on EOS counts as staged when it has the right name and is not empty. A copy cut off partway can leave a truncated file that every later `stage` skips, so delete it by hand before rerunning.
    - `stage` counts a file as in place when it copies it, finds it already on EOS and not empty, or lists it in a dry run.
    - `xrdcp` runs with no timeout, so a stuck copy can hang `stage`.
