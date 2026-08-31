# config/normalizations
## Caveats
- `measureFromNano` raises when any file is unreadable instead of returning a partial sum.
- `denominator()` returns `None` for a sample with no recorded sum.
- Cross sections are stored unfiltered and `filterEfficiencies` are applied separately.
- The luminosity value moves with the golden JSON and normtag, which is why each `source` records the exact command. Re-run it against whatever golden JSON the data was filtered with.
