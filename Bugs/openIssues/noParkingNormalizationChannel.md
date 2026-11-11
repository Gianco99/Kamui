# `vbfParking` and `bParking` have no normalization channel.

- **Where:** `config/normalizations/lumi.json:14-19`, whose `channels` block holds only `displaced`.
- **Problem:** The parking datasets record less luminosity than the full era, so no parking yield can be normalized until each channel has its own luminosity.
- **Fix:** Add a `channels` entry for each, with the luminosity its parking datasets recorded in each era.
