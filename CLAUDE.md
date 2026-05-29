# DisplacedVertices

## Documentation style
Each script has a docstring covering usage and setup — don't repeat that here. CLAUDE.md files should only capture non-obvious context: *why* a decision was made, source links for external recommendations, and caveats that aren't evident from reading the code.

## Conventions
- **camelCase** everywhere: variable names, function names, filenames, JSON keys. Intentional deviation from PEP8.
- Use `python3` not `python` — CMSSW shell breaks the system `python` binary.

## CMSSW environment
```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /uscms/home/gdecastr/nobackup/work/CMSSW_14_1_0_pre4/src/
cmsenv
```

## Structure
- `SamplesFromDAS/` — DAS querying, EOS staging, branch inspection → `SamplesFromDAS/CLAUDE.md`
- `Plotting/`       — FWLite analysis and plots → `Plotting/CLAUDE.md`
