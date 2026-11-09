# When one vertex's tracks are a subset of another's, the second vertex is always erased, even when it is the larger one.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:812-817` and `917`. The subset test passes in either direction, then `vertices->erase(v[1])` drops the second vertex. It only works because a merge writes the merged vertex into the earlier slot, so the superset nearly always comes first: on 5,196 ZH 2017 MC events it never fired, and erasing the smaller vertex instead changed no DV.
- **Kamui:** `vertexing/plugins/DVProducer.cc:266-269` and `309-310`. Reproduced on purpose, and by the standalone background-template rewrite too (`~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:600-601` and `632-634`).
- **Fix:** Erase whichever of the two holds fewer tracks.
