# Plotting

Output PNGs go in `plots/` (gitignored).

## plotJetHT.py — jet ID reference

Run 3 TightLepVeto PF JetID (`RUN3CHSruns2022FGruns2023CD`):
[PFJetIDSelectionFunctor.h](https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/SelectorUtils/interface/PFJetIDSelectionFunctor.h)

| eta region | NHF | NEF | CHF | CHM | nConst | MUF | CEF |
|---|---|---|---|---|---|---|---|
| \|η\| ≤ 2.6 | < 0.99 | < 0.90 | > 0.01 | > 0 | > 1 | < 0.8 | < 0.8 |
| 2.6 < \|η\| ≤ 2.7 | < 0.90 | < 0.99 | — | > 0 | > 1 | < 0.8 | < 0.8 |
| 2.7 < \|η\| ≤ 3.0 | < 0.99 | < 0.99 | — | — | > 1 | — | — |
| \|η\| > 3.0 (HF) | — | < 0.40 | — | — | nNeutral > 10 | — | — |

Key changes from Run 2: NHF loosened 0.9 → 0.99 in barrel; CHF/CHM boundary extended from |eta| < 2.4 to |eta| < 2.6.

**Scouting jets**: energy fraction vars exist on `Run3ScoutingPFJet` but no official JetID WP was found — [Run3PFScouting twiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/Run3PFScouting) has no selection criteria. Applying pT/eta only.
**Calo jets**: no official Run 3 ID found ([JMEDAS](https://cms-jet.github.io/JMEDAS/01-jets101/index.html)). EM fraction < 0.9 is a minimal noise veto, not an endorsed WP.
