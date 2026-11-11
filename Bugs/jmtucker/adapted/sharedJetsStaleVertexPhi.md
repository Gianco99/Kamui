# sharedJets tests every lone track of a vertex against the vertex's phi from before its first refit in the step.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1857-1859, 1896, 1921`. `phi0` is computed once per `sv0` (1857-1859), outside the loop over `sv1` (1865-1928), while `sv0` is refit inside that loop (1921). Every later `sv1` pairing tests the lone tracks (1896) against the phi from before the first refit.
- **Kamui:** `vertexing/plugins/DVProducer.cc:481, 495, 508`. Reproduced on purpose to match JMTucker.
- **Impact:** Minor: recomputing `phi0` changes DVs in 13 of 150,000 displacement-channel MC events and in no lepton-channel MC or data event.
- **Fix:** Recompute `phi0` from `sv0` at the top of each `sv1` iteration.
