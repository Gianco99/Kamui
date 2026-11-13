# A negative fit chi2 passes every chi2 cut, so a fit that failed badly is accepted.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:139, 665, 1528`. Seeding (665) keeps a fit with chi2/dof below the cut. `kv_reco_dropin` (139), used by every sharedTracks, mergeNearby and sharedJets fit, and the chi2/dof filter after zRefit (1528) drop a fit only above the cut. A negative chi2/dof is below any positive cut, so all three keep it.
- **Kamui:** `vertexing/plugins/DVProducer.cc:143, 270, 409`. Reproduced on purpose to match JMTucker, with the same one-sided tests in `fitVertex`, seeding and the filter after zRefit.
- **Rewrite:** `backgroundTemplate/2v_from_jets.cc:563, 574`. The background-template rewrite has the same tests in `fitVertex` and seeding, kept to match Alec's outputs.
- **Impact:** Minor: negative-chi2 seeds are accepted often (68 times in 20,161 lepton 2017 data events), yet rejecting them and requiring `isValid()` in `fitVertex` moves one event to another region in 17,652 signal MC events and changes no DV in 22,138 data events.
- **Fix:** Reject a negative chi2 before the chi2/dof cut in all three places. Require `isValid()` in `fitVertex` too, since a failed fit has chi2/dof 0/0 = NaN and passes the `>` test the same way.
