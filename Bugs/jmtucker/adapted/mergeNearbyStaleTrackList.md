# After a merge, mergeNearby keeps the first vertex's old track list, so a second merge in the same pass fits a stale set.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1553, 1580-1583, 1612-1613`. `tracks[0]` is filled once per `v[0]` (1553) and not refreshed when 1613 replaces `*v[0]` with the merged vertex. A second merge in the same `v[1]` loop then fits the original `v[0]` tracks plus the new `v[1]`, dropping the tracks the first partner brought in. The identical second block repeats this at 1669 and 1728-1729.
- **Kamui:** `vertexing/plugins/DVProducer.cc:414, 430-433, 440-444`. Reproduced on purpose to match JMTucker.
- **Rewrite:** `2v_from_jets.cc:674, 692`. The background-template rewrite reproduces it to match Alec's outputs.
- **Impact:** Minor: a second merge in one pass happens in about 0.4% of stop signal MC events and in none of 22,138 data or 2,652 ZH events. It changes only DVs that have 5 or more tracks either way, so no region yield moves.
- **Fix:** Set `tracks[0] = vertexTrackSet(*v[0])` right after the merged vertex replaces `*v[0]`.
