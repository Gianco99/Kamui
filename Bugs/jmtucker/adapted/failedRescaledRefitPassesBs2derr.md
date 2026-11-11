# A DV whose rescaled refit fails gets a bs2derr of 0, which passes the tight bs2derr cut.

- **JMTucker:** `MFVNeutralino/plugins/VertexAuxProducer.cc:434-452`. When the refit with rescaled track uncertainties is invalid, `rescale_bs2derr` keeps its default of 0 (`MFVNeutralinoFormats/interface/VertexAux.h:50`), and `MFVNeutralino/plugins/VertexSelector.cc:436` keeps any value below `max_rescale_bs2derr`.
- **Kamui:** `vertexing/plugins/DVProducer.cc:184-187`. Reproduced on purpose to match JMTucker: `DV_dBVErr` stays 0 when the refit fails.
- **Impact:** Minor: in the Kamui validation outputs the rescaled refit fails for 5 of 518,286 DVs, all in stop signal MC, and none of the 5 passes the other tight cuts, so the loophole has never made a DV tight.
- **Fix:** Set `DV_dBVErr` to NaN when the refit fails, so the DV fails every cut on it.
