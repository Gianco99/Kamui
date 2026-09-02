# ntupleProduction
## Caveats

- The CMSSW release is pinned in `config/sites.json`. Do not bump it! This may have unintended effects.
- Condor OS selection uses `+DesiredOS = "EL9"`. If jobs sit idle forever, try `+REQUIRED_OS = "rhel9"`.
- Each job runs `scramv1 project` from cvmfs, about 30 seconds of startup. Ship a tarball if job counts get large.
- Producers that are singletons by construction reject a `singleton` parameter, which is what `singletonImplicit` tells `kamuiTables.py` to omit.
- The schedd is recorded at submit time. LPC spreads a submission across schedds and `condor_q` asks the default one, so a task submitted elsewhere reads as finished. A `task.json` with no `schedd` key falls back to the default.
- `crab submit` returning zero means nothing: the cvmfs wrapper exits zero when CMSSW is missing, so `crab.submit` also requires that the project directory appeared.
- Retries are not published to EOS, so the `task.json` sitting next to the ntuples always describes the first attempt.
