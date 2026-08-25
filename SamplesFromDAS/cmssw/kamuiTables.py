"""
Turn a resolved content JSON into CMSSW table producers.

This is the only file in the repo that has to know about CMSSW plugin names,
and it is deliberately mechanical: every decision (what to keep, what to cut,
what precision) already lives in config/content/*.json.

The JSON it consumes is what `kamui content <preset> --write` emits - it is
already flattened, validated, and has plugin names filled in, so nothing here
needs the kamui package (which matters on a worker node).
"""

import json

import FWCore.ParameterSet.Config as cms

# Plugins that take their own fixed parameters instead of a `variables` PSet.
_FIXED = {"pileup", "genWeight"}


def _var(v):
    p = cms.PSet(
        expr=cms.string(v["expr"]),
        type=cms.string(v["type"]),
        doc=cms.string(v.get("doc", "")),
    )
    if "precision" in v:
        p.precision = cms.int32(int(v["precision"]))
    return p


def _extVar(v):
    return cms.PSet(
        src=cms.InputTag(v["src"]),
        type=cms.string(v["type"]),
        doc=cms.string(v.get("doc", "")),
    )


def _pileupTable(name, c):
    return cms.EDProducer(
        "NPUTablesProducer",
        src=cms.InputTag(c.get("src", "slimmedAddPileupInfo")),
        pvsrc=cms.InputTag("offlineSlimmedPrimaryVertices"),
        zbins=cms.vdouble([0.0, 1.7, 2.6, 3.0, 3.5, 4.2, 5.2, 6.0, 7.5, 9.0, 12.0]),
        savePtHatMax=cms.bool(False),
    )


def _genWeightTable(name, c):
    # Reuse the official configuration: the PDF/PS weight bookkeeping is intricate
    # and there is no reason to re-derive it here.
    from PhysicsTools.NanoAOD.genWeightsTable_cfi import genWeightsTable
    return genWeightsTable.clone()


def buildTables(content):
    """
    content: the dict loaded from a resolved content JSON.
    returns:  (dict of moduleName -> EDProducer, ordered list of module names)
    """
    modules = {}
    for name, c in sorted(content["collections"].items()):
        kind = c["kind"]
        modName = name[0].lower() + name[1:] + "Table"

        if kind == "pileup":
            modules[modName] = _pileupTable(name, c)
            continue
        if kind == "genWeight":
            modules[modName] = _genWeightTable(name, c)
            continue

        if kind == "global":
            mod = cms.EDProducer(
                c["plugin"],
                name=cms.string(name),
                variables=cms.PSet(**{k: _extVar(v) for k, v in c["extVariables"].items()}),
            )
            modules[modName] = mod
            continue

        mod = cms.EDProducer(
            c["plugin"],
            src=cms.InputTag(c["src"]),
            name=cms.string(name),
            doc=cms.string(c.get("doc", "")),
            extension=cms.bool(c.get("extension", False)),
            skipNonExistingSrc=cms.bool(True),
            variables=cms.PSet(**{k: _var(v) for k, v in c["variables"].items()}),
        )
        if c.get("singletonImplicit"):
            pass                       # plugin is one-per-event and rejects the parameter
        elif c.get("singleton"):
            mod.singleton = cms.bool(True)
        else:
            mod.singleton = cms.bool(False)
            mod.cut = cms.string(c.get("cut", ""))
            if "maxLen" in c:
                mod.maxLen = cms.uint32(int(c["maxLen"]))
        modules[modName] = mod

    return modules, sorted(modules)


def buildSkim(skim):
    """
    Build the HLT skim filter, or None if the content declares no skim.
    Returns (EDFilter, moduleName).
    """
    paths = skim.get("hltPaths") if skim else None
    if not paths:
        return None, None
    import HLTrigger.HLTfilters.hltHighLevel_cfi as hltHighLevel
    f = hltHighLevel.hltHighLevel.clone(
        TriggerResultsTag=cms.InputTag("TriggerResults", "", skim.get("process", "HLT")),
        HLTPaths=cms.vstring(*paths),
        andOr=cms.bool(skim.get("mode", "any") == "any"),  # any = OR of the paths
        throw=cms.bool(False),                             # a missing path must not kill the job
    )
    return f, "hltSkim"


def loadContent(path):
    with open(path) as f:
        return json.load(f)
