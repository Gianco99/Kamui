# The vertexer runs only inside `DVProducer::produce`, so the background template cannot call it on constructed events.

- **Where:** `vertexing/plugins/DVProducer.cc:244-561`, with the vertexing steps at 264-520.
- **Problem:** The template builds 2V events from pairs of DVs and has to revertex them with the same steps the ntuple production runs.
- **Fix:** Move the steps into a library that DVProducer and the template both call.
- **Decision needed:** A uniform 3.8 T field in a plain executable, as JMTucker does, or the real field map through cmsRun.
