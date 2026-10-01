"""
Turn a resolved content JSON into CMSSW table producers.
"""

# Import Block

## Standard Python imports
import json
import os

## CMSSW modules
import FWCore.ParameterSet.Config as cms


def _var(v):
    p = cms.PSet(expr=cms.string(v["expr"]), type=cms.string(v["type"]), doc=cms.string(v.get("doc", "")))
    if "precision" in v:
        p.precision = cms.int32(int(v["precision"]))
    return p


def _extVar(v):
    return cms.PSet(src=cms.InputTag(v["src"]), type=cms.string(v["type"]), doc=cms.string(v.get("doc", "")))


def _pileupTable(c):
    from PhysicsTools.NanoAOD.globals_cff import puTable
    return puTable.clone(src=cms.InputTag(c.get("src", "slimmedAddPileupInfo")), savePtHatMax=cms.bool(False))


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


def _seedTrackModules(name, c, producerName):
    """The seed-track producer and its table."""
    s = c["seeding"]
    pv, scale, drop = s["goodPv"], s["dxyErrScale"], s["trackDrop"]
    producer = cms.EDProducer(
        "SeedTrackProducer",
        src=cms.InputTag(c["src"]),
        beamSpot=cms.InputTag(s["beamSpot"]),
        primaryVertices=cms.InputTag(s["primaryVertices"]),
        goodPv=cms.PSet(
            ndofAbove=cms.double(pv["ndofAbove"]),
            maxAbsZ=cms.double(pv["maxAbsZ"]),
            rhoBelow=cms.double(pv["rhoBelow"]),
        ),
        ptAbove=cms.double(s["ptAbove"]),
        nSigmaDxyBsAbove=cms.double(s["nSigmaDxyBsAbove"]),
        minPixelLayers=cms.int32(s["minPixelLayers"]),
        minStripLayers=cms.int32(s["minStripLayers"]),
        maxFirstPixelLayer=cms.int32(s["maxFirstPixelLayer"]),
        dxyErrScale=cms.PSet(
            form=cms.string(scale["form"]),
            barrelAbsEtaBelow=cms.double(scale["barrelAbsEtaBelow"]),
            barrel=cms.vdouble(*scale["barrel"]),
            endcap=cms.vdouble(*scale["endcap"]),
        ),
        trackDrop=cms.PSet(
            coefficient=cms.double(drop["coefficient"]),
            absDxyBsCap=cms.double(drop["absDxyBsCap"]),
        ),
    )
    table = _objectTable(name, dict(c, src=producerName))
    table.externalVariables = cms.PSet(candIdx=_extVar({"src": producerName + ":candIdx", "type": "int", "doc": "Index into packedPFCandidates"}))
    return producer, table


def _vertexJetModules(name, c, corrName, updatedName):
    """The JEC, the jet update and the selection the vertexer reads."""
    from PhysicsTools.PatAlgos.recoLayer0.jetCorrFactors_cfi import patJetCorrFactors
    from PhysicsTools.PatAlgos.producersLayer1.jetUpdater_cfi import updatedPatJets
    jec = c["jec"]
    corr = patJetCorrFactors.clone(
        src=cms.InputTag(c["src"]),
        primaryVertices=cms.InputTag(jec["primaryVertices"]),
        payload=cms.string(jec["payload"]),
        levels=cms.vstring(*jec["levels"]),
    )
    updated = updatedPatJets.clone(
        jetSource=cms.InputTag(c["src"]),
        jetCorrFactorsSource=cms.VInputTag(cms.InputTag(corrName)),
    )
    selected = cms.EDFilter(
        c["plugin"],
        src=cms.InputTag(updatedName),
        cut=cms.string(c["cut"]),
        filter=cms.bool(False),
    )
    return corr, updated, selected


## Kinds whose module label is the collection stem, since they write no table
PRODUCER_ONLY_KINDS = {"vertexJet"}


def _moduleStem(name):
    """The module label a collection's producers are built under."""
    return name.lower() if name.isupper() else name[0].lower() + name[1:]


def _inputLabel(content, name):
    """The module label producing the collection another one names as an input."""
    c = content["collections"].get(name)
    if c is None:
        raise RuntimeError("Collection '%s' is named as an input but the content does not include it" % name)
    stem = _moduleStem(name)
    return stem if c["kind"] in PRODUCER_ONLY_KINDS else stem + "Producer"


def _dvModules(content, name, c, producerName):
    """The vertexer and the table of the vertices it keeps."""
    v = c["vertexing"]
    producer = cms.EDProducer(
        "DVProducer",
        seedTracks=cms.InputTag(_inputLabel(content, c["src"])),
        beamSpot=cms.InputTag(v["beamSpot"]),
        jets=cms.InputTag(_inputLabel(content, v["jets"])),
        minTracks=cms.int32(v["minTracks"]),
        maxChi2PerDof=cms.double(v["maxChi2PerDof"]),
        kalman=cms.PSet(
            maxDistance=cms.double(v["kalman"]["maxDistance"]),
            maxNbrOfIterations=cms.int32(v["kalman"]["maxIterations"]),
            doSmoothing=cms.bool(v["kalman"]["smoothing"]),
        ),
        sharedTracks=cms.PSet(**{k: cms.double(x) for k, x in v["sharedTracks"].items()}),
        zRefit=cms.PSet(**{k: cms.double(x) for k, x in v["zRefit"].items()}),
        mergeNearby=cms.PSet(**{k: cms.double(x) for k, x in v["mergeNearby"].items()}),
        sharedJets=cms.PSet(**{k: cms.double(x) for k, x in v["sharedJets"].items()}),
    )
    return producer, _objectTable(name, dict(c, src=producerName))


def buildTables(content):
    """Table producers for a resolved content dict, as (moduleName -> EDProducer, ordered names)."""
    modules = {}
    for name, c in sorted(content["collections"].items()):
        kind = c["kind"]
        modName = _moduleStem(name) + "Table"
        if kind == "pileup":
            modules[modName] = _pileupTable(c)
        elif kind == "genWeight":
            modules[modName] = _genWeightTable()
        elif kind == "global":
            modules[modName] = _globalTable(name, c)
        elif kind == "vertexJet":
            stem = _moduleStem(name)
            corrName, updatedName = stem + "CorrFactors", stem + "Updated"
            modules[corrName], modules[updatedName], modules[stem] = _vertexJetModules(name, c, corrName, updatedName)
        elif kind == "seedTrack":
            producerName = _moduleStem(name) + "Producer"
            modules[producerName], modules[modName] = _seedTrackModules(name, c, producerName)
        elif kind == "dv":
            producerName = _moduleStem(name) + "Producer"
            modules[producerName], modules[modName] = _dvModules(content, name, c, producerName)
        else:
            modules[modName] = _objectTable(name, c)

    for name, c in content["collections"].items():
        if c["kind"] != "dv":
            continue
        seedTable = modules.get(_moduleStem(c["src"]) + "Table")
        if seedTable is not None:
            link = _extVar({"src": _moduleStem(name) + "Producer:trackVertexIdx", "type": "int", "doc": "Index into the %s collection, -1 when the track is in none" % name})
            setattr(seedTable.externalVariables, _moduleStem(name) + "Idx", link)
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
    raise RuntimeError("Content JSON not found; looked for %s" % " and ".join(candidates))
