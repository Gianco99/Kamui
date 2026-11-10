# The ascending track-count insertion in sharedJets reads one past the end of sv_ascending_total_ntrack when the iterator is at end().

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1834`. When `it_ntracks` is still at `end()`, the condition reads `sv_ascending_total_ntrack[size()]`, one past the last element. It is harmless only because both branches then do the same thing, `push_back` (1835-1836) and `insert` at `end()` (1840-1841).
- **Kamui:** `vertexing/plugins/DVProducer.cc:453-457`. Not ported, since Kamui orders the vertices with a `std::stable_sort` by ascending track count, later vertex first on ties, which gives the same order as JMTucker's insertion.
- **Fix:** Remove the second half of the condition, since `insert` at `end()` already appends.
