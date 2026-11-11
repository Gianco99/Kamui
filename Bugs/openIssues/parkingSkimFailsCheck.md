# `check` fails on a Run 3 preset whose skim names a parking trigger file.

- **Where:** `python/kamui/cli.py:478-494` resolves every preset for every era of its run. `python/kamui/configReaders/content.py:164-166` refuses an era the trigger file lists no paths for, and presets have no `eras` field (`CONTENT_FIELDS`, 79).
- **Problem:** `vbfParking` lists no paths for Summer22 and Summer22EE, and `bParking` none for Summer23 and Summer23BPix, so a preset skimming on either fails for those eras. A selection naming either file needs `"eras": [...]` for the same reason.
- **Decision needed:** Add an `eras` field to presets, or have `check` skip the eras a trigger file does not list.
