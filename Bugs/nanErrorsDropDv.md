# A DV whose fit covariance is not positive definite gets NaN uncertainties and is silently dropped by the vertex selector.

- **JMTucker:** `MFVNeutralino/plugins/VertexSelector.cc:380-450`. `use_vertex` is one long conjunction of comparisons, and every comparison with a NaN uncertainty is false, including the ones set to cut nothing. `mfvVerticesAux` runs this selector in the ntuple job, so such a DV never reaches the ntuple.
- **Kamui:** `vertexing/plugins/DVProducer.cc`, `positiveDefinite` and its use in `selectionQuantities`. Reproduced on purpose: `DV_dBVErr` is NaN when the DV's position covariance is not positive definite, so the DV fails the `tightDV` cut on it.
- **Fix:** Decide deliberately: repair the covariance before computing uncertainties, or drop these DVs with an explicit cut that shows up in the cutflow.
