# Sample Caveats

Physics caveats per family are kept here so the configs stay readable.

**Exotic Higgs (exoticHiggs4d2024)**
- Run 3 ggH has no gen-HT filter. The Run 2 samples had gen-HT > 200 GeV.
- ZH and WH decays are inclusive in Run 3. For Run 2 they are exclusive to lepton decays.
- Summer24 has exclusive ZH-Zto2L and WH-WtoLNu available. They have yet to be registered.

**RPV (rpv2024)**
- One private point from Bruno. Nothing exists in Run 3 for gluino to tbs or stop to bb, official or private.

**Stealth SUSY (stealthSusy2024)**
- Private from Bruno.
- Exclusive per (mStop, mSo, ctau).
- Inclusive samples exist for Run 2. These can be filtered using `randPar`.

**Run 2 validation (run2Validation)**
- Dataset paths copied from JMTucker's `Tools/python/Samples.py`.
