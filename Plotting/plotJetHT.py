#!/usr/bin/env python3
"""
Plot per-event HT (scalar sum of jet pT) for three jet collections from a MiniAOD file:
  Run3ScoutingPFJet (HLT), slimmedCaloJets (PAT), slimmedJets (PAT, Run3 TightLepVeto ID)

Jet selection: pT > 40 GeV, |eta| < 2.6. See Plotting/CLAUDE.md for JetID cut values.
Requires cmsenv. Usage: python3 plotJetHT.py [--file URL] [--maxEvents N] [--output NAME]
"""

import argparse
import os
import ROOT
from DataFormats.FWLite import Events, Handle

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)

EOS_GGH = "root://cmseos.fnal.gov//store/user/lpcdisplacedvertices/gdecastr/Run3Samples/ggH-2S-4D_mS55_ctau10mm_2024/8e2233eb-7fb3-4d8e-94f2-a66f9b24b63d.root"

# pT > 40 GeV for HT sum — consistent with Run 2 analysis convention (JMTucker)
# https://github.com/gdecastr/nobackup/work/DVCode/mfv_10648/src/JMTucker/MFVNeutralino/src/MiniNtuple.cc
PT_MIN  = 40.0

# |eta| < 2.6 — Run 3 tracker boundary (extended from 2.4 in Run 2), CHF/CHM cuts valid up to here
# https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/SelectorUtils/interface/PFJetIDSelectionFunctor.h
ETA_MAX = 2.6

PLOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")


def tightPFJetID(jet):
    # Run 3 TightLepVeto PF JetID (RUN3CHSruns2022FGruns2023CD)
    # https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/SelectorUtils/interface/PFJetIDSelectionFunctor.h
    absEta = abs(jet.eta())
    nhf = jet.neutralHadronEnergyFraction()
    nef = jet.neutralEmEnergyFraction()
    nc  = jet.numberOfDaughters()
    chf = jet.chargedHadronEnergyFraction()
    chm = jet.chargedMultiplicity()
    muf = jet.muonEnergyFraction()
    cef = jet.chargedEmEnergyFraction()
    nn  = jet.neutralMultiplicity()

    if absEta <= 2.6:
        return nhf < 0.99 and nef < 0.90 and nc > 1 and chf > 0.01 and chm > 0 and muf < 0.8 and cef < 0.8
    elif absEta <= 2.7:
        return nhf < 0.90 and nef < 0.99 and nc > 1 and chm > 0 and muf < 0.8 and cef < 0.8
    elif absEta <= 3.0:
        return nhf < 0.99 and nef < 0.99 and nc > 1
    else:  # HF: |eta| > 3.0
        return nef < 0.40 and nn > 10


def looseCaloJetID(jet):
    # No official Run 3 calo jet ID found
    # (see https://cms-jet.github.io/JMEDAS/01-jets101/index.html). EM fraction veto is a
    # minimal noise spike rejection, not an endorsed working point.
    return jet.emEnergyFraction() < 0.9


def computeHT(jets, idFunc=None):
    ht = 0.0
    for j in jets:
        if j.pt() < PT_MIN or abs(j.eta()) > ETA_MAX:
            continue
        if idFunc and not idFunc(j):
            continue
        ht += j.pt()
    return ht


def styleHist(h, color, title):
    h.SetLineColor(color)
    h.SetLineWidth(2)
    h.SetTitle(title)


def main():
    parser = argparse.ArgumentParser(description="Plot jet HT from MiniAOD")
    parser.add_argument("--file",      default=EOS_GGH, help="Input ROOT/xrootd file")
    parser.add_argument("--maxEvents", type=int, default=-1, help="Max events to process (-1 = all)")
    parser.add_argument("--output",    default="jetHT_ggH.png", help="Output plot filename")
    args = parser.parse_args()

    events = Events(args.file)

    hScout = Handle("std::vector<Run3ScoutingPFJet>")
    hCalo  = Handle("std::vector<reco::CaloJet>")
    hPF    = Handle("std::vector<pat::Jet>")

    nBins, xLo, xHi = 60, 0, 3000

    htScout = ROOT.TH1F("htScout", "", nBins, xLo, xHi)
    htCalo  = ROOT.TH1F("htCalo",  "", nBins, xLo, xHi)
    htPF    = ROOT.TH1F("htPF",    "", nBins, xLo, xHi)

    nEvents = 0
    for event in events:
        if args.maxEvents > 0 and nEvents >= args.maxEvents:
            break
        nEvents += 1
        if nEvents % 1000 == 0:
            print(f"  Processing event {nEvents}...")

        event.getByLabel("hltScoutingPFPacker", hScout)
        event.getByLabel("slimmedCaloJets",     hCalo)
        event.getByLabel("slimmedJets",         hPF)

        # No official JetID WP for Run3ScoutingPFJet found; energy fraction vars exist on the object
        # but CMS has not published selection criteria — see https://twiki.cern.ch/twiki/bin/view/CMSPublic/Run3PFScouting
        htScout.Fill(computeHT(hScout.product()))
        htCalo .Fill(computeHT(hCalo.product(),  idFunc=looseCaloJetID))
        htPF   .Fill(computeHT(hPF.product(),    idFunc=tightPFJetID))

    print(f"Done. Processed {nEvents} events.")

    styleHist(htScout, ROOT.kBlue,  "Run3 Scouting PF jets")
    styleHist(htCalo,  ROOT.kRed,   "Slimmed Calo jets")
    styleHist(htPF,    ROOT.kBlack, "Slimmed PF jets (Run3 tight LepVeto ID)")

    os.makedirs(PLOT_DIR, exist_ok=True)

    # --- absolute counts ---
    cAbs = ROOT.TCanvas("cAbs", "Jet HT", 900, 700)
    cAbs.SetLogy()

    leg = ROOT.TLegend(0.55, 0.70, 0.88, 0.88)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    leg.AddEntry(htPF,    "Slimmed PF jets (Run3 tight LepVeto ID)", "l")
    leg.AddEntry(htScout, "Run3 Scouting PF jets",      "l")
    leg.AddEntry(htCalo,  "Slimmed Calo jets",          "l")

    htPF.GetXaxis().SetTitle("H_{T} [GeV]")
    htPF.GetYaxis().SetTitle("Events / 50 GeV")
    htPF.Draw("hist")
    htScout.Draw("hist same")
    htCalo .Draw("hist same")
    leg.Draw()

    label = ROOT.TLatex()
    label.SetNDC()
    label.SetTextSize(0.035)
    label.DrawLatex(0.12, 0.92, "ggH #rightarrow SS #rightarrow 4D  (m_{S}=55 GeV, c#tau=10mm)")
    label.DrawLatex(0.12, 0.87, f"p_{{T}} > {int(PT_MIN)} GeV, |#eta| < {ETA_MAX}")

    outAbs = os.path.join(PLOT_DIR, args.output)
    cAbs.SaveAs(outAbs)
    print(f"Saved: {outAbs}")

    # --- normalized to unity ---
    cNorm = ROOT.TCanvas("cNorm", "Jet HT normalized", 900, 700)
    cNorm.SetLogy()

    def normalize(h):
        if h.Integral() > 0:
            h.Scale(1.0 / h.Integral())

    normalize(htScout)
    normalize(htCalo)
    normalize(htPF)

    htPF.GetYaxis().SetTitle("Arbitrary units")
    htPF.Draw("hist")
    htScout.Draw("hist same")
    htCalo .Draw("hist same")
    leg.Draw()
    label.DrawLatex(0.12, 0.92, "ggH #rightarrow SS #rightarrow 4D  (m_{S}=55 GeV, c#tau=10mm)")
    label.DrawLatex(0.12, 0.87, f"p_{{T}} > {int(PT_MIN)} GeV, |#eta| < {ETA_MAX}  (normalized to unity)")

    outNorm = os.path.join(PLOT_DIR, args.output.replace(".png", "_norm.png"))
    cNorm.SaveAs(outNorm)
    print(f"Saved: {outNorm}")


if __name__ == "__main__":
    main()
