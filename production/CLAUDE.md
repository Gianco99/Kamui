# production

Sample processing: turning a DAS dataset into flat ntuples on EOS. Human-facing docs are ../README.txt and the planning documents in ../docs/.

## Layout
- The code lives in `python/kamui/`, not here. See `python/kamui/CLAUDE.md`.
- This directory holds what is specific to this stage.
- `config/` has `samples/`, `content/`, `triggers/` and `sites.json`, each with its own README and CLAUDE.md.
- `cmssw/` holds the three things that run inside CMSSW: `kamuiNtuple_cfg.py`, wiring only with no content decisions; `kamuiTables.py`, which turns resolved JSON into table producers; and `inspectMiniAOD.py`.
- `tools/triggerYields.py` computes the JMTucker comparison numbers.
- `jobs/` and `branchDumps/` are gitignored. The latter holds saved `edmDumpEventContent` output, kept as a reference for what a MiniAOD file contains.

## Things That Will Bite
- **The CMSSW release is pinned** in `config/sites.json`, which is what the condor jobs read. Newer releases read older files, so it is chosen to be recent rather than campaign-matched. Do not bump it without asking Gianfranco: a release change can introduce errors repo-wide.
- **`electronID('name')` throws on an unknown name**, while `bDiscriminator()` quietly returns -1000 for a tagger that is not there. Campaigns carry different IDs, which is why the Run 2 presets override them. Run `python3 cmssw/inspectMiniAOD.py <file>` to list what a given file actually embeds before assuming.
- **Some table producers are singletons by construction** and reject a `singleton` parameter. `content.py` marks those with `singletonImplicit` so `kamuiTables.py` knows to omit it.
- **Two collections are uncapped on purpose.** `GenPart` takes no cut, because `genPartIdxMother` indexes the source collection and any cut silently corrupts the mother links. `PV` takes no `maxLen`, because capping it would also cap `nPV` and break pileup counting. Both look like oversights.
- **Condor OS selection** uses `+DesiredOS = "EL9"`. If jobs sit idle forever, try `+REQUIRED_OS = "rhel9"`. Unverified against a real submission.
- **Each condor job runs `scramv1 project` from cvmfs**, roughly 30 seconds of startup. Ship a tarball if job counts get large.
- **Two EDM output modules in one CRAB task**, from `--output both`, is unverified. If CRAB refuses it, run two tasks.
