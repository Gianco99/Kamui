# select/

Everything behind the `select`, `cutflow` and `norm` commands. Inputs are the ntuples a production task wrote; outputs are ntuples with the same branches, plus a cutflow.

`engine.py` - Applies a resolved selection. It reads the input ntuples with uproot, builds one mask per cut in the order the config lists them, writes the surviving events, and returns the cutflow. It knows six kinds of cut: `trigger`, `object`, `flags`, `quantity`, `veto` and `anyOf`. Any cut can carry `invert`, which keeps exactly the events it would otherwise have thrown away. It also computes the per-track impact parameters and the jet identification, which the ntuples store as raw ingredients rather than finished quantities.

`quantities.py` - The event-level quantities a selection config may name, each with the branches it needs and a one-line description. `HT40`, `caloHT30`, `nJet40`, `leadMuonPt` and `MET` are among them, and the TightLepVeto jet identification the jet-based ones apply lives here too.

`io.py` - Finds the input ntuples for a sample inside a production task, over xrootd or on a local disk, and writes and prints the cutflow.

`batch.py` - Builds the condor job area for a selection pass under `ntupleSelection/jobs/<task>/`, packages the kamui source so a worker can import it, and submits. The area holds `submit.jdl`, `jobList.txt`, `fileLists.json`, one `selection_<era>.json` and one `runSelect_<selection>_<era>.sh` per era, `kamuiPackage.tar.gz`, `task.json` and `logs/`. `--dryRun` leaves all of it on disk unsubmitted, which is how to read the exact configuration a job would use.

`runOne.py` - What a worker runs: `python3 -m kamui.select.runOne <selectionJson> <outputFile> <input> [input ...]`. It applies the already-resolved selection to one group of files and writes the cutflow beside the output.

`normalization.py` - The generator sums a sample must be normalized by. It sums the run-level counters over a sample's central NanoAOD, read remotely over xrootd, and raises rather than returning a short sum when a file cannot be read.

## Jet ID Working Points

Kept because jets.json deliberately stores raw energy fractions rather than a precomputed ID flag, so the working points are applied downstream and this is the table to apply.

Run 3 TightLepVeto PF JetID (RUN3CHSruns2022FGruns2023CD), from PFJetIDSelectionFunctor.h:
https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/SelectorUtils/interface/PFJetIDSelectionFunctor.h

  |eta|         NHF      NEF      CHF     CHM   nConst          MUF     CEF
  <= 2.6        < 0.99   < 0.90   > 0.01  > 0   > 1             < 0.8   < 0.8
  2.6 - 2.7     < 0.90   < 0.99   -       > 0   > 1             < 0.8   < 0.8
  2.7 - 3.0     < 0.99   < 0.99   -       -     > 1             -       -
  > 3.0 (HF)    -        < 0.40   -       -     nNeutral > 10   -       -

Changes from Run 2: NHF loosened from 0.9 to 0.99 in the barrel, and the CHF/CHM boundary moved from |eta| < 2.4 to < 2.6. The Run 2 presets use CHS slimmedJets and therefore the Run 2 working points, not this table.

Two related gaps, both checked 2026-08. Scouting jets carry the energy-fraction variables on Run3ScoutingPFJet but no official JetID working point exists; the Run3PFScouting twiki lists no criteria. Calo jets have no official Run 3 ID either.

Run 2 TightLepVeto as implemented, in python/kamui/select/quantities.py, recorded 2026-08-28. The selection picks the function by era, and an era with no entry raises.

2016 and 2016APV, tightLepVeto2016:

  NHF < 0.90 and NEF < 0.99 at every eta, and inside |eta| < 2.4 additionally NEF < 0.90, nConst > 1, MUF < 0.80, CHF > 0, CHM > 0, CEF < 0.80.

2017 and 2018, tightLepVeto2017p8:

  NHF < 0.90, NEF < 0.90, nConst > 1, MUF < 0.80, CHF > 0, CHM > 0, CEF < 0.80, applied at every eta the jet collection reaches, which is |eta| < 2.5.

The 2017/18 row carries a deliberate deviation from the published working point, which drops the charged requirements beyond |eta| = 2.4 where the tracker ends. JMTucker's jet_cuts_2017p8 in Tools/python/PATTupleSelection_cfi.py is a flat conjunction with no eta split, so a jet between 2.4 and 2.5 has no tracks, fails CHF > 0, and never enters its selection. Applying the published split admits those jets, which moves HT and the jet pT ladders in the displacement-triggered channel. The Run 2 selections are validated against JMTucker event for event, so the flat form is what reproduces them. Their 2016 cut does carry the split, which is why the two eras differ here.
