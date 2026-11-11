# The normalization files are validated but never linked to samples.

- **Where:** `python/kamui/configReaders/normalizations.py:27-50` (`validateNormalizations`) checks their format. No sample field names the cross section entry that normalizes it.
- **Problem:** Nothing ties a sample to its process and filter efficiency, so no Kamui step can scale a yield to a cross section.
- **Fix:** Give each sample a link to its cross section entry once a Kamui step reads the normalization files. Parked until then.
