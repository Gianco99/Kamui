# The 3x5 and 4x5 regions count only DVs with exactly 5 tracks, so an event with a 3-track or 4-track DV and a 6-or-more-track DV is in no two-DV region.

- **JMTucker:** `MFVNeutralino/python/VertexSelector_cfi.py:132-133` and `MFVNeutralino/python/MiniTree_cff.py:27-28`. `mfvSelectedVerticesTightNtk3or5` and `mfvSelectedVerticesTightNtk4or5` set `max_ntracks = 5`, and the 3x5 and 4x5 cuts ask for leading DVs of exactly 5 and 3, or 5 and 4, tracks, while every other "5-track" category means 5 or more.
- **Kamui:** `config/selections/run2/dv3x5.json` and `config/selections/run2/dv4x5.json`. Reproduced on purpose: the 5-track count has `"max": 5`.
- **Fix:** Drop `"max": 5` from the 5-track count in both, so 4x5 means exactly one DV with 5 or more tracks and at least one with 4, and 3x5 means exactly one with 5 or more, none with 4, and at least one with 3.
