# Grid

This folder holds everything that reaches outside our own machine. The datasets we analyze live on the grid, the network of computing sites that store CMS data. DAS is the catalog of those datasets and their files. For example, `./kamui query --family <family>` asks DAS, through `das.py`, how many files, events and GB each sample holds.

`das.py`: Asks DAS what datasets and files exist, and caches every answer on disk. It also finds a sample's central NanoAOD, the officially produced NanoAOD of the same dataset, because `norm` reads the generator weight sum from it.

`fetch.py`: Copies a sample's MiniAOD files from the grid to EOS, under `<stageoutBase>/<miniaodDir>/<sample>/`.

Both need `cmsenv` and a valid grid proxy.
