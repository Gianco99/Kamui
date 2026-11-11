# The ggHPTH80 and compressed-stop samples have no filter efficiency and no 13.6 TeV cross section.

- **Where:** `config/normalizations/exoticHiggs.json`, which holds only a `run2` block. No file in `config/normalizations/` covers compressed stop.
- **Problem:** These samples cannot be normalized to a cross section.
- **Fix:** Add the 13.6 TeV cross sections and filter efficiencies: a `run3` block in `exoticHiggs.json` for ggHPTH80, and a normalization file for compressed stop.
