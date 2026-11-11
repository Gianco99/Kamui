# Condor selection passes cannot be resubmitted, and `status` reports their held jobs only as a count.

- **Where:** `python/kamui/cli.py:422-423` refuses a selection pass. `python/kamui/submit/condor.py:304-353` (`resubmit`) finds its job area through the production `taskDir` (307). `_selectionStatus` (`cli.py:395-412`) shows the queue in one line (405).
- **Problem:** A failed or held selection job has to be rerun by hand, and `status` gives none of the `condor_q -hold` and `condor_rm` hints that production tasks get from `_queueLines` (`condor.py:250-260`).
- **Fix:** Give `condor.resubmit` a job-area argument (it already hands that area to `_recordRetry`), and let `resubmit` find a pass's missing jobs with `missingJobs` in `python/kamui/select/batch.py`.
