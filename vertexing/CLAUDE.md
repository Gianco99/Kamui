# Vertexing

- Seed tracks keep `packedPFCandidates` order.
- `DxyErrScale` scales only the dxy diagonal of the covariance.
- The `dxyErrScale` forms are JMTucker's formulas written out literally.
- NOTE: Track dropping is planned but not yet included.

- Plugin names are global across CMSSW. Check `edmPluginDump` before naming a new one.
