# A DV whose rescaled refit fails gets a bs2derr of 0, which passes the tight bs2derr cut.

- **JMTucker:** `MFVNeutralino/plugins/VertexAuxProducer.cc:432-452`. When the refit with rescaled track uncertainties is invalid, `rescale_bs2derr` keeps its default of 0 (`MFVNeutralinoFormats/interface/VertexAux.h:50`), and `MFVNeutralino/plugins/VertexSelector.cc:436` keeps any value below `max_rescale_bs2derr`.
- **Kamui:** `vertexing/plugins/DVProducer.cc:166-169`. Reproduced on purpose: `DV_dBVErr` stays 0 when the refit fails.
- **Fix:** Set `DV_dBVErr` to NaN when the refit fails, so the DV fails every cut on it.
