# Condor jobs cannot apply a lumiMask, so data samples with one have to run on CRAB.

- **Where:** `python/kamui/submit/condor.py:89-92` refuses such a sample. The job's source in `ntupleProduction/cmssw/ntuple_cfg.py:42-46` sets no `lumisToProcess`.
- **Problem:** Data filtered by the golden JSON can only be produced on CRAB.
- **Fix:** Apply the mask in the condor job through `lumisToProcess`, then drop the refusal.
