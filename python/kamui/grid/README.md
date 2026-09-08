# Grid

Everything that reaches outside our own machine.

`das.py` - Asks DAS what datasets and files exist, caches every answer on disk, and works out the central NanoAOD twin a sample's generator weight sum comes from.

`fetch.py` - Copies raw MiniAOD from the grid to our EOS area.

Both need `cmsenv` and a valid grid proxy. See `python/kamui/README.md` for the commands that drive them.
