# ntupleProduction

Sample processing: turning a DAS dataset into ntuples on EOS. Human-facing docs are README.md here and the planning documents in ../docs/.

## Layout
- The submission code lives in `python/kamui/submit/`; see `python/kamui/CLAUDE.md`. This directory holds what runs inside CMSSW and the generated job areas.
- `cmssw/` holds the three things that run inside CMSSW: `kamuiNtuple_cfg.py`, wiring only with no content decisions; `kamuiTables.py`, which turns resolved JSON into table producers; and `inspectMiniAOD.py`.
- The configs this stage reads are in `../config/`: `samples/`, `content/`, `triggers/` and `sites.json`, each with its own README and CLAUDE.md. `../tools/triggerYields.py` computes the JMTucker comparison numbers.
- `jobs/` and `branchDumps/` are gitignored. The latter holds saved `edmDumpEventContent` output, kept as a reference for what a MiniAOD file contains.

## Things That Will Bite
- **The CMSSW release is pinned** in `config/sites.json`, which is what the condor jobs read. Newer releases read older files, so it is chosen to be recent rather than campaign-matched. Do not bump it without asking Gianfranco: a release change can introduce errors repo-wide.
- **`electronID('name')` throws on an unknown name**, while `bDiscriminator()` quietly returns -1000 for a tagger that is not there. Campaigns carry different IDs, which is why the Run 2 presets override them. Run `python3 cmssw/inspectMiniAOD.py <file>` to list what a given file actually embeds before assuming.
- **Some table producers are singletons by construction** and reject a `singleton` parameter. `content.py` marks those with `singletonImplicit` so `kamuiTables.py` knows to omit it.
- **Two collections are uncapped on purpose.** `GenPart` takes no cut, because `genPartIdxMother` indexes the source collection and any cut silently corrupts the mother links. `PV` takes no `maxLen`, because capping it would also cap `nPV` and break pileup counting. Both look like oversights.
- **Condor OS selection** uses `+DesiredOS = "EL9"`. If jobs sit idle forever, try `+REQUIRED_OS = "rhel9"`. Unverified against a real submission.
- **Each condor job runs `scramv1 project` from cvmfs**, roughly 30 seconds of startup. Ship a tarball if job counts get large.
- **Two EDM output modules in one CRAB task**, from `--output both`, is unverified. If CRAB refuses it, run two tasks.

## Submission Bookkeeping
- **The schedd is recorded at submit time.** LPC spreads a submission over several schedds and `condor_q` asks the default one unless told otherwise, so a task submitted elsewhere reads as finished. `condor.submit` parses `submit jobs to <schedd>` out of `condor_submit`'s stdout into `task.json`, and both `status` and the still-queued check pass it back with `-name`. A `task.json` with no `schedd` key predates this or came from a `condor_submit` that worded its output differently, and those two callers then fall back to the default schedd.
- **`crab submit` returning zero means nothing.** The cvmfs `crab` wrapper exits zero when the CMSSW environment is missing, so the return code alone does not say whether anything was submitted. `crab.submit` also requires that `<workArea>/crab_<requestName>` appeared. `_projectDir` reads those two values back out of the generated config, so a config edited by hand is still checked against the directory it would really create.
- **Retries are not published to EOS.** `publishRecord` runs at submit; `_recordRetry` only touches the local `task.json`. The copy sitting next to the ntuples always describes the first attempt.

## Resubmission
- **What counts as failed is what is missing from EOS**, since a condor job that died anywhere before its `xrdcp` leaves nothing behind and there is no other record of it. `missingJobs` lists each sample's output directory once and looks for `<sample>_<tag>_<index>.root` per row of `jobList.txt`, two names per row when the task was submitted with `--output both`.
- **An unlistable EOS directory reads as an empty one.** `_eosListing` returns an empty set for any non-zero `xrdfs ls`, so an expired proxy or a wrong `outDirBase` looks exactly like a task where every job failed, and the retry would then rerun everything. The `outputs N/M present on EOS` line is the thing to read before letting it submit.
- **The retry JDL is built by string replacement on `submit.jdl`**, matching the column-aligned lines the `JDL` template writes verbatim. Reformatting that template silently breaks retries, so there is a guard that raises "its format has changed" instead of submitting jobs that would write their logs over the first attempt's.
- **A dry-run resubmit writes nothing at all**, not even the job list, so the retry number it prints stays free and the real attempt is still retry 1.
- **A queued job is not a failed job**, and rerunning it would write the same output name twice, so `resubmit` refuses while any of the task's clusters still have jobs. That check silently passes when it cannot work the answer out: `_queuedJobs` returns 0 when `task.json` records no `condorCluster`, and when `condor_q` fails for any reason.
- **CRAB needs none of this.** It tracks its own failed jobs and writes retried output to the same place, so `crab.resubmit` is a loop over the projects in the work area. The one thing it does not do is keep the earlier attempt's logs separate, which is the whole reason the condor side has retry numbering.
