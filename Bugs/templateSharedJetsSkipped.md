# The template's revertexer skips sharedJets, which MiniTree inputs cannot support.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:1206-1375` (Alec's uncommitted version, snapshot of 2026-11-05), commented out. JMTucker's Vertexer runs it with `resolve_shared_jets = True` (`MFVNeutralino/plugins/Vertexer.cc:1780-1962`), and a MiniTree keeps no track-jet association, so the step cannot be ported exactly.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces it on purpose: `~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:724` (`revertexPair`).
- **Fix:** Build the template from inputs that keep the track-jet association, such as Kamui ntuples, and run sharedJets as DVProducer does.
