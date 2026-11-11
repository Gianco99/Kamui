# The central Summer24 StopStopto2Dbar2D grid is not registered in the catalog.

- **Where:** `config/samples/run3/rpv2024.json:6`, the single private point the family holds.
- **Problem:** The central grid has 24 points of 200k events each and supersedes that private point.
- **Fix:** Register the 24 central points in place of the private one.
