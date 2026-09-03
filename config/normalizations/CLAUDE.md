# Normalization Caveats
## General Caveats

- Cross sections are stored unfiltered and `filterEfficiencies` are applied separately.
- The luminosity value moves with the golden JSON and normtag, which is why each Run 3 `source` records the exact brilcalc command. Re-run it against whatever golden JSON the data was filtered with.

## Cross Section Caveats

Physics caveats per model are kept here so the configs stay readable.

**Exotic Higgs (exoticHiggs.json)**
- Higgs production at MH = 125 GeV, assuming BR(H -> LLP) = 1.
- Run 2 numbers assume a center-of-mass energy of 13 TeV. The exotic Higgs cross-sections would have to be updated for Run 3's center of mass energy.
- The Run 2 VH samples are generated with leptonic decays only, so their cross sections are just summed over the three lepton flavors.
- `ZH` is the qq-initiated piece, with the gg component split off into `ggZH`.
- Even though the `filterEfficiencies` are keyed by scalar mass, the filter itself is on gen-HT.

