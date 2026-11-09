# sharedJets tests all of a vertex's lone tracks against the vertex's phi from before its first refit in this step, so later refits never update that phi.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1857-1859, 1896, 1921`. `phi0` is computed once per sv0 at 1857-1859, outside the loop over sv1 (1865-1928), and `sv0` is refit at 1921 inside that loop, so every later sv1 pairing tests the lone tracks at 1896 against the phi of the vertex before its first refit.
- **Kamui:** `vertexing/plugins/DVProducer.cc:454, 468, 481`. Reproduced on purpose to match JMTucker.
- **Fix:** Recompute `phi0` from `sv0` at the top of each sv1 iteration.
