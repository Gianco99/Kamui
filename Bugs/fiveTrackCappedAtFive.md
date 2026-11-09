# The 4x5 region counts only DVs with exactly 5 tracks, so an event with a 4-track and a 6-or-more-track DV is in no two-DV region.

- **JMTucker:** `MFVNeutralino/python/VertexSelector_cfi.py:133` and `MFVNeutralino/python/MiniTree_cff.py:28`. `mfvSelectedVerticesTightNtk4or5` sets `max_ntracks = 5`, and the 4x5 cut asks for leading DVs of exactly 5 and 4 tracks, while every other "5-track" category means 5 or more.
- **Kamui:** `config/selections/run2/dv4x5.json`. Reproduced on purpose: the 5-track count has `"max": 5`.
- **Fix:** Drop `"max": 5` from the 5-track count, so 4x5 means exactly one DV with 5 or more tracks and at least one with 4.
