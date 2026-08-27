"""
cmsRun configuration: MiniAOD in, one flat ROOT tree out.

All content decisions come from a resolved content JSON (see
config/content/). This file only wires things together, so it
should almost never need editing.

Local run:
    cmsRun kamuiNtuple_cfg.py \
        content=/path/to/dvSignal.resolved.json \
        inputFiles=root://cmseos.fnal.gov//store/.../file.root \
        outputFile=test.root maxEvents=1000

On a worker node the resolved JSON travels with the job, so `content` is just
a filename in the scratch directory.

Output tree: `Events`, flat, readable with uproot/RDataFrame - no CMSSW needed
downstream. run / luminosityBlock / event are written automatically.
"""

import os
import sys

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())   # on a worker node kamuiTables.py sits next to the pset
from kamuiTables import buildSkim, buildTables, loadContent  # noqa: E402

opts = VarParsing("analysis")
opts.register("content",     "",        VarParsing.multiplicity.singleton, VarParsing.varType.string,
              "path to a resolved content JSON")
opts.register("isMC",        True,      VarParsing.multiplicity.singleton, VarParsing.varType.bool,
              "MC (True) or data (False)")
opts.register("globalTag",   "",        VarParsing.multiplicity.singleton, VarParsing.varType.string,
              "conditions global tag; empty means take it from the input file")
opts.register("nThreads",    1,         VarParsing.multiplicity.singleton, VarParsing.varType.int,
              "number of cmsRun threads")
opts.register("reportEvery", 1000,      VarParsing.multiplicity.singleton, VarParsing.varType.int,
              "MessageLogger reporting interval")
opts.register("output",      "",        VarParsing.multiplicity.singleton, VarParsing.varType.string,
              "what to write: ntuple, miniaod, or both. Empty means 'both' if the content "
              "declares a miniaod block, else 'ntuple'.")
opts.register("miniaodFile", "dvSlim.root", VarParsing.multiplicity.singleton, VarParsing.varType.string,
              "filename for the slimmed MiniAOD output")
opts.setDefault("outputFile", "kamuiNtuple.root")
opts.setDefault("maxEvents", -1)
opts.parseArguments()

if not opts.content:
    raise RuntimeError("content=<resolved content JSON> is required")
content = loadContent(opts.content)

process = cms.Process("DVNTUPLE")
process.load("FWCore.MessageService.MessageLogger_cfi")
process.MessageLogger.cerr.FwkReport.reportEvery = opts.reportEvery
process.load("Configuration.StandardSequences.Services_cff")

process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(opts.maxEvents))
process.source = cms.Source(
    "PoolSource",
    fileNames=cms.untracked.vstring(*opts.inputFiles),
    duplicateCheckMode=cms.untracked.string("noDuplicateCheck"),
)
process.options = cms.untracked.PSet(
    numberOfThreads=cms.untracked.uint32(opts.nThreads),
    numberOfStreams=cms.untracked.uint32(opts.nThreads),
    wantSummary=cms.untracked.bool(False),
)

# Conditions: only loaded when a tag is given. The tables built here read
# quantities already stored in MiniAOD, so nothing needs the EventSetup yet.
# A tag becomes necessary once JECs or a re-vertexing step are added.
if opts.globalTag:
    process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
    from Configuration.AlCa.GlobalTag import GlobalTag
    process.GlobalTag = GlobalTag(process.GlobalTag, opts.globalTag, "")

# ---- content -> table producers -------------------------------------------------
modules, order = buildTables(content)
for name, mod in modules.items():
    setattr(process, name, mod)
process.kamuiTables = cms.Task(*[getattr(process, n) for n in order])

# ---- optional HLT skim ----------------------------------------------------------
skimFilter, skimName = buildSkim(content.get("skim", {}))
if skimFilter is not None:
    setattr(process, skimName, skimFilter)
    process.dvPath = cms.Path(getattr(process, skimName), process.kamuiTables)
    selectEvents = cms.untracked.PSet(SelectEvents=cms.vstring("dvPath"))
else:
    process.dvPath = cms.Path(process.kamuiTables)
    selectEvents = cms.untracked.PSet()   # keep every event

# ---- output ---------------------------------------------------------------------
trig = content.get("triggerBits", {})
outputCommands = [
    "drop *",
    "keep nanoaodFlatTable_*Table_*_*",
    "keep nanoaodMergeableCounterTable_*Table_*_*",
    "keep nanoaodUniqueString_nanoMetadata_*_*",
]
if trig.get("keepAll", True):
    # The output module turns edm::TriggerResults into one bool branch per HLT path.
    outputCommands.append("keep edmTriggerResults_*_*_%s" % trig.get("process", "HLT"))

miniaodCfg = content.get("miniaod", {})
# Default is the flat tree only. A content preset may DEFINE a miniaod keep list
# without every job paying for it; ask for it with output=miniaod or output=both.
mode = opts.output or "ntuple"
if mode not in ("ntuple", "miniaod", "both"):
    raise RuntimeError(f"output={mode} is not one of ntuple / miniaod / both")
if mode in ("miniaod", "both") and not miniaodCfg:
    raise RuntimeError(f"output={mode} but content preset '{content.get('name')}' has no miniaod block")

endPaths = []
if mode in ("ntuple", "both"):
    process.out = cms.OutputModule(
        "NanoAODOutputModule",
        fileName=cms.untracked.string(opts.outputFile),
        outputCommands=cms.untracked.vstring(*outputCommands),
        compressionLevel=cms.untracked.int32(9),
        compressionAlgorithm=cms.untracked.string("LZMA"),
        dataset=cms.untracked.PSet(
            filterName=cms.untracked.string(""),
            dataTier=cms.untracked.string("NANOAODSIM" if opts.isMC else "NANOAOD"),
        ),
        SelectEvents=selectEvents,
    )
    process.endNtuple = cms.EndPath(process.out)
    endPaths.append("ntuple -> " + opts.outputFile)

if mode in ("miniaod", "both"):
    # Same skim as the tree, so the two outputs always describe the same events.
    process.slimOut = cms.OutputModule(
        "PoolOutputModule",
        fileName=cms.untracked.string(opts.miniaodFile),
        outputCommands=cms.untracked.vstring(*miniaodCfg["outputCommands"]),
        compressionLevel=cms.untracked.int32(9),
        compressionAlgorithm=cms.untracked.string("LZMA"),
        dataset=cms.untracked.PSet(
            filterName=cms.untracked.string(""),
            dataTier=cms.untracked.string("MINIAODSIM" if opts.isMC else "MINIAOD"),
        ),
        SelectEvents=selectEvents,
        overrideInputFileSplitLevels=cms.untracked.bool(True),
    )
    process.endMiniaod = cms.EndPath(process.slimOut)
    endPaths.append("slimmed MiniAOD -> " + opts.miniaodFile)

print("[kamui] content preset : %s (isMC=%s)" % (content.get("name"), content.get("isMC")))
print("[kamui] output         : %s" % "; ".join(endPaths))
print("[kamui] collections    : %s" % ", ".join(sorted(content["collections"])))
if skimFilter is not None:
    print("[kamui] HLT skim       : %s" % ", ".join(content["skim"]["hltPaths"]))
