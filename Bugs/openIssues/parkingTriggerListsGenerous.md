# The parking trigger lists hold every path that ran unprescaled at some point in an era, so MC efficiencies from them are an upper bound.

- **Where:** `config/triggers/run3/vbfParking.json` and `config/triggers/run3/bParking.json`.
- **Problem:** Summer23 VBF parking includes the Mjj720 pair (`vbfParking.json:9-10`), unprescaled only in the first 2023C menu. Summer24 B parking includes Mu7 and Mu8, which start in 2024E, and Mu6 and Mu0, which start in 2024F (`bParking.json:18-21`). The 2022 `HLT_Mu12_IP6` recorded only toward the end of fills. Nothing weights a path by the luminosity it collected within its era. No 2025 paths are listed, since there is no 2025 MC era.
- **Decision needed:** Weight each path by the luminosity it recorded unprescaled within its era, or quote the MC efficiencies as upper bounds.
