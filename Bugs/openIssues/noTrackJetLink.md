# The ntuples keep no link from tracks to jets, so the template's sharedJets step has no input.

- **Where:** `vertexing/plugins/DVProducer.cc:203-222` (`matchedJet`) finds a track's jet and is called at 461 for the tracks of each DV, but none of the products put at 551-560 holds the result.
- **Problem:** Running sharedJets in the background template, the fix proposed in `Bugs/backgroundTemplate/templateSharedJetsSkipped.md`, needs each track's jet.
- **Fix:** Have DVProducer write each seed track's matched jet index.
