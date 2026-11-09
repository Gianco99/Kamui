# Seeding keeps a fit strictly below maxChi2PerDof, while every later fit passes at or below it.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:665, 139, 1528`. Seeding requires `normalisedChiSquared() < max_seed_vertex_chi2`, while `kv_reco_dropin` and the chi2/dof filter after zRefit drop a fit only when its chi2/dof is `> 5`, so a fit exactly at the cut fails as a seed and passes everywhere else.
- **Kamui:** `vertexing/plugins/DVProducer.cc:243, 139, 382`. Reproduced on purpose to match JMTucker, with `<` at seeding and `>` in `fitVertex` and the filter after zRefit. The standalone background-template rewrite does the same (`~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:563, 574`).
- **Fix:** Use one comparison everywhere, for example keep a seed when its chi2/dof is `<= maxChi2PerDof`.
