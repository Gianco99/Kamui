# mergeNearby keeps the first vertex's original track list after a merge, so a second merge in the same sweep fits the stale set.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1553, 1580-1583, 1612-1613`. `tracks[0]` is filled once per v[0] at 1553 and never refreshed when 1613 replaces `*v[0]` with the merged vertex, so a second merge in the same v[1] loop fits the original v[0] tracks plus the new v[1] and drops the tracks the first partner brought in. The second, identical `resolve_split_vertices_tight` block repeats this at 1669 and 1728-1729.
- **Kamui:** `vertexing/plugins/DVProducer.cc:387, 403-406, 413-417`. Reproduced on purpose to match JMTucker, and by the standalone background-template rewrite too (`~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:674` and `692`).
- **Fix:** Set `tracks[0] = vertexTrackSet(*v[0])` right after the merged vertex replaces `*v[0]`.
