# The template's revertexer skips zRefit and the chi2/dof cleanup after it.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:1025-1094` (Alec's uncommitted version, snapshot of 2026-11-05), commented out on purpose: Alec reasons that the input vertices already passed it. JMTucker's Vertexer runs it between sharedTracks and mergeNearby (`MFVNeutralino/plugins/Vertexer.cc:1371-1534`), so the vertices that sharedTracks rebuilds never get it, while real 2V events do. The effect is not measured yet.
- **Kamui:** Kamui's DVProducer runs zRefit. The standalone template rewrite skips it on purpose: `2v_from_jets.cc:724` (`revertexPair`).
- **Fix:** Run zRefit in the revertexer, as DVProducer does, and measure the change in the template.
