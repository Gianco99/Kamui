# h_output_<step>_vertex_mostisotrack is booked with 0 bins and never filled, so each output step writes an empty histogram.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:485`. The booking asks for 0 bins between 0 and 4, which ROOT answers with a "nbins is <=0 - set to nbins = 1" warning and a single bin over [0, 4]. Nothing in the file fills `hs_output_vertex_mostisotrack` (declared at 281), so the histogram stays empty.
- **Kamui:** `vertexing/plugins/DVProducer.cc:86-112`. Not ported, since the Kamui constructor books no histograms.
- **Fix:** Remove the declaration and booking, or give the histogram real bins and fill the largest track dR per vertex in `fillCommonOutputHists`.
