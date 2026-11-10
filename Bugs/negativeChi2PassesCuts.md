# A negative fit chi2 passes every chi2 cut, so a fit that failed badly is accepted.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:139, 665, 1528`. Seeding (665) keeps a fit whose chi2/dof is below the cut, while `kv_reco_dropin` (139), which every sharedTracks, mergeNearby and sharedJets fit goes through, and the chi2/dof filter after zRefit (1528) drop a fit only when its chi2/dof is above the cut. A negative chi2/dof sits below any positive cut, so all three accept it.
- **Kamui:** `vertexing/plugins/DVProducer.cc:139, 249, 388`. Reproduced on purpose to match JMTucker, with the same one-sided tests in `fitVertex`, seeding and the filter after zRefit. The standalone background-template rewrite has the same tests in `fitVertex` and seeding (`2v_from_jets.cc:563, 574`).
- **Fix:** Reject a fit with a negative chi2 before the chi2/dof cut in all three places. Require `isValid()` in `fitVertex` too, since a failed fit has chi2/dof 0/0 = NaN and passes the `>` test the same way.
