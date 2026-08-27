"""
Event-level quantities a selection config may name.
"""

# Import Block

## Standard Python imports
import awkward as ak


## Branches the jet identification needs
JET_ID_BRANCHES = ["Jet_pt", "Jet_eta", "Jet_neHEF", "Jet_neEmEF", "Jet_chHEF",
                   "Jet_chEmEF", "Jet_muEF", "Jet_nConstituents", "Jet_chMultiplicity"]


## Eras whose TightLepVeto definition is the 2016 one rather than the 2017/18 one
ERAS_2016 = {"2016", "2016APV"}


def tightLepVeto2017p8(events):
    """
    TightLepVeto PF jet ID for 2017 and 2018, as the Run 2 analysis defines it.

    The ntuples deliberately keep raw fractions rather than a precomputed flag, so the
    working point lives here.

    The charged requirements apply at every eta, with no barrel/endcap split. The published
    TightLepVeto working point drops them beyond |eta| = 2.4, where the tracker ends, but
    JMTucker's jet_cuts_2017p8 is a flat conjunction (Tools/python/PATTupleSelection_cfi.py),
    so a jet between 2.4 and 2.5 has no tracks, fails chHEF > 0, and never enters the
    selection. Reinstating the split admits those jets and moves HT and the jet ladders.
    The 2016 cut in the same file does carry the split, which is why tightLepVeto2016 keeps it.
    """
    return (events["Jet_neHEF"] < 0.90) & (events["Jet_neEmEF"] < 0.90) \
        & (events["Jet_nConstituents"] > 1) & (events["Jet_muEF"] < 0.80) \
        & (events["Jet_chHEF"] > 0) & (events["Jet_chMultiplicity"] > 0) & (events["Jet_chEmEF"] < 0.80)


def tightLepVeto2016(events):
    """
    TightLepVeto PF jet ID for 2016 and 2016APV.

    Two things differ from 2017/18: the neutral electromagnetic fraction is loose (0.99)
    outside |eta| < 2.4 and tight (0.90) inside it, and the constituent and muon-fraction
    requirements apply only inside |eta| < 2.4.
    """
    central = (events["Jet_neEmEF"] < 0.90) & (events["Jet_nConstituents"] > 1) \
        & (events["Jet_muEF"] < 0.80) & (events["Jet_chHEF"] > 0) \
        & (events["Jet_chMultiplicity"] > 0) & (events["Jet_chEmEF"] < 0.80)
    ok = (events["Jet_neHEF"] < 0.90) & (events["Jet_neEmEF"] < 0.99)
    return ok & ak.where(abs(events["Jet_eta"]) < 2.4, central, True)


# The identification a jet must pass is a property of the data-taking year, so every caller has
# to say which year it means. Guessing here would silently bias a whole era's yields.
def tightLepVeto(events, era):
    """TightLepVeto PF jet ID for an era."""
    if era in ERAS_2016:
        return tightLepVeto2016(events)
    if era in ("2017", "2018"):
        return tightLepVeto2017p8(events)
    raise ValueError(
        f"no TightLepVeto jet identification is defined for era '{era}'. "
        "The Run 2 working points are here; the Run 3 table is in docs/JetID.txt and still needs writing down."
    )


def selectedJets(events, minPt, era, maxEta=2.5, applyId=True):
    """Mask of jets passing pT, eta and, by default, the era's TightLepVeto identification."""
    keep = (events["Jet_pt"] > minPt) & (abs(events["Jet_eta"]) < maxEta)
    if applyId:
        keep = keep & tightLepVeto(events, era)
    return keep


## Every quantity a selection config may reference, and the branches it needs
def htFromJets(events, minJetPt, era, maxEta=2.5, applyId=True):
    """Scalar sum of pT over identified jets above a threshold."""
    return ak.sum(events["Jet_pt"][selectedJets(events, minJetPt, era, maxEta, applyId)], axis=1)


def countJets(events, minPt, era, maxEta=2.5, applyId=True):
    """Number of identified jets above a pT threshold."""
    return ak.sum(selectedJets(events, minPt, era, maxEta, applyId), axis=1)


def caloJetHt(events, minPt, maxEta=2.5):
    """
    Scalar sum of pT over calo jets above a threshold.

    Calo jets carry no identification and no jet energy correction: the displaced-dijet
    triggers cut on the raw quantity, so this sums the raw pT the ntuple stored.
    """
    keep = (events["CaloJet_pt"] > minPt) & (abs(events["CaloJet_eta"]) < maxEta)
    return ak.sum(events["CaloJet_pt"][keep], axis=1)


def leadingPt(events, collection):
    """pT of the highest-pT object in a collection, or 0 when the collection is empty."""
    pt = events[collection + "_pt"]
    return ak.fill_none(ak.max(pt, axis=1), 0.0)


def count(events, collection):
    """Number of objects in a collection."""
    return events["n" + collection]


QUANTITIES = {
    "HT40":            {"fn": lambda e, era: htFromJets(e, 40.0, era), "branches": JET_ID_BRANCHES, "doc": "Scalar sum of pT over jets above 40 GeV with |eta| < 2.5 passing TightLepVeto"},
    "HT30":            {"fn": lambda e, era: htFromJets(e, 30.0, era), "branches": JET_ID_BRANCHES, "doc": "Scalar sum of pT over jets above 30 GeV with |eta| < 2.5 passing TightLepVeto"},
    "nJet20":          {"fn": lambda e, era: countJets(e, 20.0, era),  "branches": JET_ID_BRANCHES, "doc": "Jets above 20 GeV with |eta| < 2.5 passing TightLepVeto"},
    "nJet40":          {"fn": lambda e, era: countJets(e, 40.0, era),  "branches": JET_ID_BRANCHES, "doc": "Jets above 40 GeV with |eta| < 2.5 passing TightLepVeto"},
    "caloHT30":        {"fn": lambda e, era: caloJetHt(e, 30.0), "branches": ["CaloJet_pt", "CaloJet_eta"], "doc": "Scalar sum of raw pT over calo jets above 30 GeV with |eta| < 2.5, the quantity the displaced-dijet triggers cut on"},
    "nCaloJet":        {"fn": lambda e, era: count(e, "CaloJet"), "branches": ["nCaloJet"], "doc": "Number of calo jets, the whole collection with no requirement"},
    "leadMuonPt":      {"fn": lambda e, era: leadingPt(e, "Muon"),     "branches": ["Muon_pt"],     "doc": "pT of the leading muon"},
    "leadElectronPt":  {"fn": lambda e, era: leadingPt(e, "Electron"), "branches": ["Electron_pt"], "doc": "pT of the leading electron"},
    "leadJetPt":       {"fn": lambda e, era: leadingPt(e, "Jet"),      "branches": ["Jet_pt"],      "doc": "pT of the leading jet"},
    "nJet":            {"fn": lambda e, era: count(e, "Jet"),      "branches": ["nJet"],      "doc": "Number of jets"},
    "nMuon":           {"fn": lambda e, era: count(e, "Muon"),     "branches": ["nMuon"],     "doc": "Number of muons"},
    "nElectron":       {"fn": lambda e, era: count(e, "Electron"), "branches": ["nElectron"], "doc": "Number of electrons"},
    "nSV":             {"fn": lambda e, era: count(e, "SV"),       "branches": ["nSV"],       "doc": "Number of secondary vertices"},
    "MET":             {"fn": lambda e, era: e["MET_pt"],          "branches": ["MET_pt"],    "doc": "Missing transverse energy"},
}


def evaluate(name, events, era):
    """Compute a named quantity over an array of events."""
    if name not in QUANTITIES:
        raise ValueError(f"unknown quantity '{name}'. Known quantities: {', '.join(sorted(QUANTITIES))}")
    return QUANTITIES[name]["fn"](events, era)


def branchesFor(name):
    """Branches a named quantity needs to be read from the ntuple."""
    if name not in QUANTITIES:
        raise ValueError(f"unknown quantity '{name}'. Known quantities: {', '.join(sorted(QUANTITIES))}")
    return list(QUANTITIES[name]["branches"])
