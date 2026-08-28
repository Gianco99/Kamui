"""
cmsRun configuration: MiniAOD in, one ntuple out.

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

Output tree: `Events`, one entry per event, readable with uproot/RDataFrame - no CMSSW needed
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
## The generator-weight producer accumulates the run-level sums that normalization divides by,
## so it has to see every event. Keeping it behind the skim would make the denominator count
## only the events that survived, which silently inflates every yield from a skimmed sample.
normNames = [n for n in order if "genweight" in n.lower()]
tableNames = [n for n in order if n not in normNames]
process.kamuiTables = cms.Task(*[getattr(process, n) for n in tableNames])


# ---- optional HLT skim ----------------------------------------------------------
skimFilter, skimName = buildSkim(content.get("skim", {}))
if skimFilter is not None:
    setattr(process, skimName, skimFilter)
    process.dvPath = cms.Path(getattr(process, skimName), process.kamuiTables)
    selectEvents = cms.untracked.PSet(SelectEvents=cms.vstring("dvPath"))
else:
    process.dvPath = cms.Path(process.kamuiTables)
    selectEvents = cms.untracked.PSet()   # keep every event

## Unfiltered and scheduled, not in a Task: a Task runs its modules only when something
## consumes their products, which would again mean only the events that survived the skim.
if normNames:
    normSeq = getattr(process, normNames[0])
    for n in normNames[1:]:
        normSeq = normSeq + getattr(process, n)
    process.normPath = cms.Path(normSeq)

# ---- output ---------------------------------------------------------------------
trig = content.get("triggerBits", {})
outputCommands = [
    "drop *",
    "keep nanoaodFlatTable_*Table_*_*",
    "keep nanoaodMergeableCounterTable_*Table_*_*",
    "keep nanoaodUniqueString_nanoMetadata_*_*",
]
if trig.get("keepAll", True):
    # The output module turns edm::TriggerResults into one bool branch per path.
    # Several processes are kept because the HLT decisions and the MET filter decisions
    # live in different ones, and a process absent from a given file simply matches nothing.
    processes = trig.get("processes") or [trig.get("process", "HLT")]
    for proc in processes:
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
