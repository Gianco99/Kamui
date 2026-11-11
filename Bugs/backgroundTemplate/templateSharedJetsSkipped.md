# The template's revertexer skips sharedJets, which MiniTree inputs cannot support.

- **Template code:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:1206-1375` (Alec's uncommitted 2026-11-05 version) is commented out. JMTucker's Vertexer runs the step with `resolve_shared_jets = True` (`MFVNeutralino/plugins/Vertexer.cc:1780-1962`), and a MiniTree keeps no track-jet association, so the step cannot be ported exactly.
- **Kamui:** No template code yet.
- **Rewrite:** `2v_from_jets.cc:724` (`revertexPair`). Skipped to match Alec's outputs.
- **Impact:** Changes physics results, by an amount not yet measured: real 2V events lose tracks in sharedJets when their two DVs share a jet, constructed pairs never do, and these pairs make up the 5x5 limit template. MiniTree inputs keep no track-jet association, so the size cannot be measured with them.
- **Fix:** Build the template from inputs that keep the track-jet association, such as Kamui ntuples, and run sharedJets as DVProducer does.
