# Several histogram fills skip the histos guard, so running with histos = False dereferences pointers that were never set.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:699-700, 1439-1450, 1527, 1893`. These fill `h_failedseed_vertex_chi2`, `h_failedseed_vertex_isvalid`, the `h_dz_vertex_*` histograms, `h_dz_vertex_chi2` and `h_resolve_shared_jets_lonetrkvtx_dphi`, which are booked only inside `if (histos)` (389-543), and the pointers are never initialized, so with histos = False the first fill dereferences a garbage pointer. All of them are reached with the other `mfvVertices` defaults (`max_nm1_refit_distz_sig > 0`, `resolve_shared_jets = True`).
- **Kamui:** `vertexing/plugins/DVProducer.cc:239-245, 381-383`. Not ported, since Kamui books no histograms and its seeding and post-zRefit filter fill nothing.
- **Fix:** Wrap each of these fills in `if (histos)`, and initialize every histogram pointer to `nullptr` in the class.
