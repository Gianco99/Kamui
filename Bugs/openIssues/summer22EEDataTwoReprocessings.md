# Summer22EE data spans two reprocessings, and `sites.json` gives the era one data global tag.

- **Where:** `config/sites.json:14`.
- **Problem:** 2022 E data was reprocessed with `130X_dataRun3_v2`, while F and G use the registered `130X_dataRun3_PromptAnalysis_v1`, so 2022 E data would run with the wrong global tag.
- **Fix:** Give 2022 E its own era entry in `sites.json` before any 2022 E data runs.
