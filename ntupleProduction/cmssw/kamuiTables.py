"""Turn a resolved content JSON into CMSSW table producers."""

import json
import os

import FWCore.ParameterSet.Config as cms


def _var(v):
    p = cms.PSet(expr=cms.string(v["expr"]), type=cms.string(v["type"]), doc=cms.string(v.get("doc", "")))
    if "precision" in v:
        p.precision = cms.int32(int(v["precision"]))
    return p


def _extVar(v):
    return cms.PSet(src=cms.InputTag(v["src"]), type=cms.string(v["type"]), doc=cms.string(v.get("doc", "")))


def _pileupTable(c):
    return cms.EDProducer(
        "NPUTablesProducer",
        src=cms.InputTag(c.get("src", "slimmedAddPileupInfo")),
        pvsrc=cms.InputTag("offlineSlimmedPrimaryVertices"),
        zbins=cms.vdouble([0.0, 1.7, 2.6, 3.0, 3.5, 4.2, 5.2, 6.0, 7.5, 9.0, 12.0]),
        savePtHatMax=cms.bool(False),
    )


def _genWeightTable():
    ## The official configuration, since the PDF and PS weight bookkeeping is intricate.
    from PhysicsTools.NanoAOD.genWeightsTable_cfi import genWeightsTable
    return genWeightsTable.clone()


def _globalTable(name, c):
    return cms.EDProducer(
        c["plugin"],
        name=cms.string(name),
        variables=cms.PSet(**{k: _extVar(v) for k, v in c["extVariables"].items()}),
    )


def _objectTable(name, c):
    mod = cms.EDProducer(
        c["plugin"],
        src=cms.InputTag(c["src"]),
        name=cms.string(name),
        doc=cms.string(c.get("doc", "")),
        skipNonExistingSrc=cms.bool(True),
        variables=cms.PSet(**{k: _var(v) for k, v in c["variables"].items()}),
    )
    ## A plugin that is one-per-event by construction rejects the parameter entirely.
    if c.get("singletonImplicit"):
        return mod
    if c.get("singleton"):
        mod.singleton = cms.bool(True)
        return mod
    mod.singleton = cms.bool(False)
    mod.cut = cms.string(c.get("cut", ""))
    if "maxLen" in c:
        mod.maxLen = cms.uint32(int(c["maxLen"]))
    return mod


def buildTables(content):
    """Table producers for a resolved content dict, as (moduleName -> EDProducer, ordered names)."""
    modules = {}
    for name, c in sorted(content["collections"].items()):
        kind = c["kind"]
        modName = name[0].lower() + name[1:] + "Table"
        if kind == "pileup":
            modules[modName] = _pileupTable(c)
        elif kind == "genWeight":
            modules[modName] = _genWeightTable()
        elif kind == "global":
            modules[modName] = _globalTable(name, c)
        else:
            modules[modName] = _objectTable(name, c)
    return modules, sorted(modules)


def buildSkim(skim):
    """The HLT skim filter as (EDFilter, moduleName), or (None, None) when the content declares no skim."""
    paths = skim.get("hltPaths") if skim else None
    if not paths:
        return None, None
    import HLTrigger.HLTfilters.hltHighLevel_cfi as hltHighLevel
    ## throw=False because one path list serves every era and a path absent from a year never fires.
    f = hltHighLevel.hltHighLevel.clone(
        TriggerResultsTag=cms.InputTag("TriggerResults", "", skim.get("process", "HLT")),
        HLTPaths=cms.vstring(*paths),
        andOr=cms.bool(skim.get("mode", "any") == "any"),
        throw=cms.bool(False),
    )
    return f, "hltSkim"


def loadContent(path):
    """Load a resolved content JSON, accepting either a full path or a bare filename in the working directory."""
    candidates = [path, os.path.basename(path)]
    for c in candidates:
        if os.path.isfile(c):
            with open(c) as f:
                return json.load(f)
    raise RuntimeError("content JSON not found; looked for %s" % " and ".join(candidates))
