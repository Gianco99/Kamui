# Kamui's `DV_dBVErr` NaN rule covers only JMTucker's first vertex selector pass.

- **Where:** `vertexing/plugins/DVProducer.cc:150-167` (`jmtErrorsFinite`), applied at 188-189.
- **Problem:** JMTucker's `mfvVertexSequence` runs its vertex selector again, as `mfvVerticesAux`, after `mfvVerticesToJets` ties jets to DVs by shared tracks, and two of its miss distances to the PV then use the jets' momentum. Kamui has no such association, so a DV that only the second pass drops stays in Kamui. None turned up in the validation against JMTucker, where every DV that could be compared agrees.
- **Fix:** Add the two jet terms to `jmtErrorsFinite` once a jet-to-DV association exists.
