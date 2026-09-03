"""cmsRun configuration: MiniAOD in, ntuple out. Content comes from a resolved content JSON."""

import os
import sys

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())
from kamuiTables import buildSkim, buildTables, loadContent  # noqa: E402

SINGLETON = VarParsing.multiplicity.singleton

opts = VarParsing("analysis")
opts.register("content", "", SINGLETON, VarParsing.varType.string, "Path to a resolved content JSON")
opts.register("isMC", True, SINGLETON, VarParsing.varType.bool, "MC (True) or data (False)")
opts.register("globalTag", "", SINGLETON, VarParsing.varType.string, "Conditions global tag; empty takes it from the input file")
opts.register("nThreads", 1, SINGLETON, VarParsing.varType.int, "Number of cmsRun threads")
opts.register("reportEvery", 1000, SINGLETON, VarParsing.varType.int, "MessageLogger reporting interval")
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

if opts.globalTag:
    process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
    from Configuration.AlCa.GlobalTag import GlobalTag
    process.GlobalTag = GlobalTag(process.GlobalTag, opts.globalTag, "")

modules, order = buildTables(content)
for name, mod in modules.items():
    setattr(process, name, mod)

## The generator-weight producer must see every event, so it is kept out of the skimmed path.
normNames = [n for n in order if "genweight" in n.lower()]
tableNames = [n for n in order if n not in normNames]
process.kamuiTables = cms.Task(*[getattr(process, n) for n in tableNames])

skimFilter, skimName = buildSkim(content.get("skim", {}))
if skimFilter is not None:
    setattr(process, skimName, skimFilter)
    process.dvPath = cms.Path(getattr(process, skimName), process.kamuiTables)
    selectEvents = cms.untracked.PSet(SelectEvents=cms.vstring("dvPath"))
else:
    process.dvPath = cms.Path(process.kamuiTables)
    selectEvents = cms.untracked.PSet()

## Scheduled
if normNames:
    normSeq = getattr(process, normNames[0])
    for n in normNames[1:]:
        normSeq = normSeq + getattr(process, n)
    process.normPath = cms.Path(normSeq)

trig = content.get("triggerBits", {})
outputCommands = [
    "drop *",
    "keep nanoaodFlatTable_*Table_*_*",
    "keep nanoaodMergeableCounterTable_*Table_*_*",
    "keep nanoaodUniqueString_nanoMetadata_*_*",
]
for proc in trig.get("processes") or [trig.get("process", "HLT")]:
    outputCommands.append("keep edmTriggerResults_*_*_%s" % proc)

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

print("[kamui] content preset : %s (isMC=%s)" % (content.get("name"), content.get("isMC")))
print("[kamui] output         : %s" % opts.outputFile)
print("[kamui] collections    : %s" % ", ".join(sorted(content["collections"])))
if skimFilter is not None:
    print("[kamui] HLT skim       : %s" % ", ".join(content["skim"]["hltPaths"]))
