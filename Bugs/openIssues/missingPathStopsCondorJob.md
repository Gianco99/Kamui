# On condor, a selection job whose own files lack every path of a trigger cut stops, even when the sample's other files have them.

- **Where:** `python/kamui/select/engine.py:90-96` (`_triggerCut`) and `137-138` (`_anyOfCut`) look only at the branches of the files one call reads (`_readAll`, 415-454). `python/kamui/select/batch.py:95-96` gives each condor job a few of a sample's files, while a local pass reads them all at once (`python/kamui/select/io.py:228`).
- **Problem:** When a sample's files come from different HLT menus, as in data, a job whose files all lack a cut's paths stops with `NoTriggerPath`, so the same pass can run locally and fail on condor depending on how the files fall into jobs. `_flagsCut` (99-107) stops a job the same way on a flag its files lack.
- **Fix:** Let a job count a path or flag its files lack as not fired and say so in its cutflow note, and have `cutflow` stop on a sample where every job lacks it.
