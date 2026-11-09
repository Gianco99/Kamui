# The second pairing loop guards the b-tagged, npv <= 20 category with the wrong list, so a category with a single vertex of 5 or more tracks hangs the job.

- **JMTucker:** `MFVNeutralino/test/One2Two/2v_from_jets.cc:4112` (Alec's uncommitted version, snapshot of 2026-11-05) tests `dbv_value_vector_btag_npult20.size()`, while `4119` draws from the `_5trk` list. With two or more vertices in the category and only one with 5 or more tracks, the draw can only return the anchor itself and repeats forever. It did not fire in production; small pools (single years, 20% data, MC with b tags or npu splits) make it likely.
- **Kamui:** Not in Kamui yet. The standalone template rewrite reproduces the guard on purpose (`~/nobackup/work/BackgroundTemplateRebuild/rewrite/2v_from_jets.cc:790-791`, `drawPartner`) and stops with an error where the original would hang (`802`).
- **Fix:** Test the `_5trk` list, as the other categories do.
