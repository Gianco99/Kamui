# The staged tutorial MiniAOD on EOS is 0 bytes.

- **Where:** The copy of `tutorialZH2018` that `./kamui stage` made on EOS for user gdecastr, in the folder that `stageoutBase` and `miniaodDir` in `config/sites.json` name. `python/kamui/grid/fetch.py:26-40` (`_listStaged`) counts an empty file as missing.
- **Problem:** A failed copy left an empty file under the right name, so anything that reads it directly finds no events.
- **Fix:** Rerun `./kamui stage --name tutorialZH2018`, which copies it again.
