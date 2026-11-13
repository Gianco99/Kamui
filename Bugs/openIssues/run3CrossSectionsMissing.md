# No Run 3 sample has a cross section, and the ggHPTH80 and compressed-stop samples have no filter efficiency.

- **Where:** `config/normalizations/exoticHiggs.json`, the only cross section file, holds only a `run2` block, at 13 TeV.
- **Problem:** No Run 3 sample can be normalized to a cross section.
- **Fix:** Add a `run3` block at 13.6 TeV to `exoticHiggs.json`, with the ggHPTH80 filter efficiency, and a cross section file for each other model, with the compressed-stop filter efficiency.
