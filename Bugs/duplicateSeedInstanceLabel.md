# Two track collections are put under the one instance label "seed", so the event keeps an empty collection under it.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:385, 600-601`. The constructor declares `produces<reco::TrackCollection>("seed")` once, and `finish` puts `tracks_seed` and then `tracks_missseed` under "seed". CMSSW's `Event::put` overwrites the slot without a warning, so the stored "seed" collection is always `tracks_missseed`, which is created empty at 548 and never filled, and the seed tracks are lost.
- **Kamui:** `vertexing/plugins/DVProducer.cc:107-111`. Not ported, since Kamui makes no debug track collections.
- **Fix:** Delete the `tracks_missseed` put, or declare it with its own label and put it there.
