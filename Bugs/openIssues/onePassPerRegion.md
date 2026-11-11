# Each region needs its own full select pass, which re-reads every input.

- **Where:** `python/kamui/select/engine.py:363-389` (`applySelection`) reads the inputs (`_readAll`, 415-454) and applies one selection.
- **Problem:** A region runs stacked after its channel, as in `lepton,dv3x4`, so covering every region reads the same ntuples and applies the same channel cuts once per region.
- **Decision needed:** Let one pass fan out over several regions after a shared channel prefix.
