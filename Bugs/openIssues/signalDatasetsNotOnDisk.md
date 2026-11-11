# 256 of the 3,661 Run 3 signal datasets cannot be read directly.

- **Where:** The Run 3 sample files in `config/samples/run3/`.
- **Problem:** 226 are on tape only, mostly exotic Higgs 4d in Summer22 to Summer23BPix (ttH alone is 46). The other 30 have their only disk copy at a T3, including 15 W+H 4b Summer24 at T3_US_Colorado, which xrootd could not open. A DAS site query for each dataset (`dasgoclient -query="site dataset=<dataset>"`) shows where its copies are.
- **Fix:** Recall them to disk with a Rucio rule before reading them.
