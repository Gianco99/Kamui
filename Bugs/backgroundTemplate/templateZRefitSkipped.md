# The template's revertexer skips zRefit and the chi2/dof cleanup after it.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:1025-1094` (Alec's uncommitted 2026-11-05 version) is commented out on purpose: Alec reasons that the input vertices already passed it. JMTucker's Vertexer runs it between sharedTracks and mergeNearby (`MFVNeutralino/plugins/Vertexer.cc:1371-1534`), so the vertices that sharedTracks rebuilds in a constructed event never get it, while real 2V events do.
- **Kamui:** `backgroundTemplate/2v_from_jets.cc:724` (`revertexPair`). Skipped to match Alec's outputs. DVProducer runs zRefit and the cleanup (`vertexing/plugins/DVProducer.cc:384-410`).
- **Impact:** Changes physics results, by an amount not yet measured: the revertexed track counts decide which pairs enter the 5x5 limit template, and in the lepton 5x5 run about half of the trials with two inputs of 5 or more tracks come back with new track sets, which never get zRefit.
- **Fix:** Run zRefit in the revertexer, as DVProducer does, and measure the change in the template.
