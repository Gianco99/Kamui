"""
Turns a content config into a form the cmsRun config consumes. The file format is documented in config/content/README.md.
"""

# Import Block

## Standard Python imports
import os

## Kamui modules
from ..foundations import paths
from ..foundations.config import RUNS, eraGroup, isNameList, loadJson, loadWithIncludes, runDir
from .requirements import cutString, resolveRequirements

# CMSSW plugin language
KIND_TO_PLUGIN = {
    "patJet":           "SimplePATJetFlatTableProducer",
    "patMuon":          "SimplePATMuonFlatTableProducer",
    "patElectron":      "SimplePATElectronFlatTableProducer",
    "patPhoton":        "SimplePATPhotonFlatTableProducer",
    "patTau":           "SimplePATTauFlatTableProducer",
    "patMET":           "SimplePATMETFlatTableProducer",
    "packedCandidate":  "SimplePATCandidateFlatTableProducer",
    "isolatedTrack":    "SimplePATIsolatedTrackFlatTableProducer",
    "vertex":           "SimpleVertexFlatTableProducer",
    "secondaryVertex":  "SimpleSecondaryVertexFlatTableProducer",
    "genParticle":      "SimpleGenParticleFlatTableProducer",
    "candidate":        "SimpleCandidateFlatTableProducer",
    "beamSpot":         "SimpleBeamspotFlatTableProducer",
    "genEvent":         "SimpleGenEventFlatTableProducer",
    "global":           "GlobalVariablesTableProducer",
    "pileup":           "NPUTablesProducer",
    "genWeight":        "GenWeightsTableProducer",
    "seedTrack":        "SimpleTrackFlatTableProducer",
    "vertexJet":        "PATJetSelector",
    "dv":               "SimpleVertexFlatTableProducer",
    "dvTrack":          "SimpleTrackFlatTableProducer",
}

# Kinds whose producer needs conditions
CONDITIONS_KINDS = {"vertexJet", "dv"}

# Kinds the vertexing plugins consume, which write no table
PRODUCER_ONLY_KINDS = {"vertexJet"}

# Kinds whose CMSSW producer decides its own branches (config/content/README.md)
FIXED_CONTENT_KINDS = {"pileup", "genWeight"}
# Kinds that are inherently one-per-event
ALWAYS_SINGLETON_KINDS = {"beamSpot", "genEvent"}
# `global` uses externalVariables-style entries (src/type/doc).
EXTVAR_KINDS = {"global"}

VALID_TYPES = {"float", "double", "int", "uint", "int16", "uint16", "uint8", "bool"}


def listPresets(contentDir=None):
    """Presets an era defines, as {era: [names]}. Only presets/ is read, since those are what a sample names."""
    contentDir = contentDir or paths.CONTENT_DIR
    out = {}
    for era in sorted(os.listdir(contentDir)):
        d = os.path.join(contentDir, era, "presets")
        if os.path.isdir(d):
            out[era] = sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))
    return out


def listCollections(contentDir=None):
    """Collections an era defines, as {era: [names]}."""
    contentDir = contentDir or paths.CONTENT_DIR
    out = {}
    for era in sorted(os.listdir(contentDir)):
        d = os.path.join(contentDir, era, "collections")
        if os.path.isdir(d):
            out[era] = sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))
    return out


## Every top-level key a content config may carry
CONTENT_FIELDS = {"collections", "triggerBits", "skim"}


def contentDirs(era, contentDir=None):
    """Search path for a content config: only that era's own set, so a Run 3 config can never reach a Run 2 sample."""
    return [runDir(contentDir or paths.CONTENT_DIR, era)]


def resolveContent(name, contentDir=None, isMC=True, era="Summer24"):
    """Flatten a preset's include chain and translate it into what a job receives."""
    cfg = loadWithIncludes(name, contentDirs(era, contentDir))

    unknown = sorted(set(cfg) - CONTENT_FIELDS)
    if unknown:
        raise ValueError(f"Content config '{name}' has unknown key(s) {unknown}; valid keys are {sorted(CONTENT_FIELDS)}")
    if not cfg.get("collections"):
        raise ValueError(f"Content config '{name}' defines no collections; check the spelling of 'include'")

    collections = {}
    for cname, c in cfg.get("collections", {}).items():
        if not isinstance(c, dict):
            raise ValueError(f"Content config '{name}': collection '{cname}' must be an object, got {type(c).__name__}")
        if c.get("mcOnly") and not isMC:
            continue
        if c.get("dataOnly") and isMC:
            continue
        collections[cname] = _translate(cname, c, era, isMC)

    return {
        "name":        name,
        "isMC":        isMC,
        "needsConditions": any(c["kind"] in CONDITIONS_KINDS for c in collections.values()),
        "collections": collections,
        "triggerBits": _checkTriggerBits(name, cfg["triggerBits"]) if "triggerBits" in cfg else {},
        "skim":        _resolveSkim(cfg.get("skim", {}), era),
    }


## Every key a triggerBits block may carry
TRIGGER_BITS_FIELDS = {"processes"}


def _checkTriggerBits(name, bits):
    """The processes whose trigger decisions a job keeps. The list is looped over in the job, so a single string would be read letter by letter."""
    where = f"Content config '{name}': triggerBits"
    if not isinstance(bits, dict) or set(bits) != TRIGGER_BITS_FIELDS:
        raise ValueError(f"{where} must be an object holding only {sorted(TRIGGER_BITS_FIELDS)}")
    if not isNameList(bits["processes"]):
        raise ValueError(f"{where} has processes {bits['processes']!r}; it must be a non-empty list of process names, such as [\"HLT\", \"PAT\"]")
    return {"processes": list(bits["processes"])}


## Every key a trigger config may carry once its includes are merged
TRIGGER_FIELDS = {"paths", "mode", "process"}

## How a trigger config combines its paths: any is an OR, all an AND
TRIGGER_MODES = ("any", "all")


def _readTriggerConfig(name, searchDir):
    """A trigger config with its includes merged and every field checked, with paths still one list for every era or an object keyed by era. The name of the file for error messages comes with it."""
    trig = loadWithIncludes(name, searchDir)
    where = f"Trigger config '{name}' in {os.path.relpath(searchDir, paths.CONFIG_DIR)}"
    unknown = sorted(set(trig) - TRIGGER_FIELDS)
    if unknown:
        raise ValueError(f"{where} has unknown key(s) {unknown}; valid keys are {sorted(TRIGGER_FIELDS | {'include'})}")
    pathList = trig.get("paths")
    if not isNameList(pathList) and not (isinstance(pathList, dict) and pathList and all(isNameList(v) for v in pathList.values())):
        raise ValueError(f"{where} needs 'paths', a non-empty list of HLT path patterns or an object mapping each era to one")
    mode = trig.get("mode", "any")
    if mode not in TRIGGER_MODES:
        raise ValueError(f"{where} has mode {mode!r}; it must be 'any' or 'all'")
    process = trig.get("process", "HLT")
    if not isinstance(process, str) or not process:
        raise ValueError(f"{where} has process {process!r}; it must be a process name such as 'HLT'")
    return {"paths": pathList, "mode": mode, "process": process}, where


def loadTriggerConfig(name, era=None, triggerDir=None):
    """A trigger config with its includes merged and every field checked, as paths, mode and process with the defaults filled in. It is read from the era's run folder unless triggerDir names one, and paths keyed by era give that era's list."""
    trig, where = _readTriggerConfig(name, triggerDir or runDir(paths.TRIGGERS_DIR, era))
    pathList = trig["paths"]
    if isinstance(pathList, dict):
        if era is None:
            raise ValueError(f"{where} keys its paths by era, so it needs one of: {', '.join(pathList)}")
        ## An era the file leaves out is one where the channel never existed, so it never borrows another era's paths
        if era not in pathList:
            raise ValueError(f"{where} lists no paths for era '{era}'; it lists {', '.join(pathList)}")
        pathList = pathList[era]
    return {"paths": list(pathList), "mode": trig["mode"], "process": trig["process"]}


def triggerEras(name, triggerDir=None):
    """The eras a trigger config keys its paths by, empty when one list serves every era. It is read from triggerDir, or from the whole trigger folder."""
    pathList = _readTriggerConfig(name, triggerDir or paths.TRIGGERS_DIR)[0]["paths"]
    return list(pathList) if isinstance(pathList, dict) else []


## Every key a skim block may carry
SKIM_FIELDS = {"triggers", "mode", "process"}


def _resolveSkim(skim, era):
    """
    Expand a skim block.
    """
    if not skim:
        return {}
    unknown = sorted(set(skim) - SKIM_FIELDS)
    if unknown:
        raise ValueError(f"Skim has unknown key(s) {unknown}; valid keys are {sorted(SKIM_FIELDS)}")
    name = skim.get("triggers")
    if not name:
        return {}
    if not isinstance(name, str):
        raise ValueError(f"Skim triggers {name!r} must name one trigger config")
    trig = loadTriggerConfig(name, era)
    out = dict(skim)
    mode = skim.get("mode", trig["mode"])
    if mode not in TRIGGER_MODES:
        raise ValueError(f"Skim mode '{mode}' is not 'any' or 'all'")
    process = skim.get("process", trig["process"])
    if not isinstance(process, str) or not process:
        raise ValueError(f"Skim process {process!r} must be a process name such as 'HLT'")
    out.update({
        "triggers":  name,
        "hltPaths":  trig["paths"],
        "mode":      mode,
        "process":   process,
    })
    return out


## Every key a collection may carry
COLLECTION_FIELDS = {"type", "src", "doc", "cut", "maxLen", "variables", "singleton", "mcOnly", "dataOnly", "seeding", "jec", "requirements", "vertexing"}
VARIABLE_FIELDS = {"expr", "type", "doc", "precision"}
EXTVAR_FIELDS = {"src", "type", "doc"}


def _translate(cname, c, era, isMC):
    unknown = sorted(set(c) - COLLECTION_FIELDS)
    if unknown:
        raise ValueError(f"Collection '{cname}' has unknown key(s) {unknown}; valid keys are {sorted(COLLECTION_FIELDS)}")
    kind = c.get("type")
    if kind not in KIND_TO_PLUGIN:
        raise ValueError(f"Collection '{cname}': unknown type '{kind}'. Known types: {', '.join(sorted(KIND_TO_PLUGIN))}")
    ## Only the producer-only kinds choose their objects with requirements and re-apply JECs, so on any other kind the two keys would be ignored
    for k in ("jec", "requirements"):
        if k in c and kind not in PRODUCER_ONLY_KINDS:
            raise ValueError(f"Collection '{cname}': '{k}' has no meaning on a '{kind}' collection, since only a {' or '.join(sorted(PRODUCER_ONLY_KINDS))} collection reads it")

    out = {
        "plugin":    KIND_TO_PLUGIN[kind],
        "kind":      kind,
        "doc":       c.get("doc", ""),
    }
    if kind in FIXED_CONTENT_KINDS:
        if "src" in c:
            out["src"] = c["src"]
        return out

    if kind in EXTVAR_KINDS:
        for k in ("cut", "maxLen", "singleton"):
            if k in c:
                raise ValueError(f"Collection '{cname}': '{k}' has no meaning on a '{kind}' collection")
        out["extVariables"] = _checkExtVars(cname, c.get("variables", {}))
        return out

    if "src" not in c:
        raise ValueError(f"Collection '{cname}': missing 'src'")
    out["src"] = c["src"]

    if kind in PRODUCER_ONLY_KINDS:
        for k in ("variables", "cut", "maxLen", "singleton"):
            if k in c:
                raise ValueError(f"Collection '{cname}': '{k}' has no meaning on a '{kind}' collection, which writes no table")
        out["jec"] = _checkJec(cname, c.get("jec"))
        where = f"Collection '{cname}'"
        out["cut"] = cutString(resolveRequirements(where, c.get("requirements"), era), _jetVariableExprs(era), where)
        ## ntupleTables.py names the module from this flag, since nothing on the CMSSW side may import the package
        out["writesTable"] = False
        return out

    out["variables"] = _checkVars(cname, c.get("variables", {}))
    if kind == "dv":
        for k in ("cut", "maxLen", "singleton"):
            if k in c:
                raise ValueError(f"Collection '{cname}': '{k}' has no meaning on a 'dv' collection, since SeedTrack_dvIdx indexes every vertex it writes")
        out["vertexing"] = _checkVertexing(cname, c.get("vertexing"), era, isMC)
    elif "vertexing" in c:
        raise ValueError(f"Collection '{cname}': 'vertexing' has no meaning on a '{kind}' collection")
    if kind == "seedTrack":
        out["seeding"] = _resolveSeeding(cname, c.get("seeding"), era, isMC)
    elif "seeding" in c:
        raise ValueError(f"Collection '{cname}': 'seeding' has no meaning on a '{kind}' collection")
    if kind in ALWAYS_SINGLETON_KINDS:
        for k in ("cut", "maxLen"):
            if k in c:
                raise ValueError(f"Collection '{cname}': '{k}' has no meaning on a singleton collection")
        # These plugins are one-per-event by construction and reject a `singleton` parameter
        out["singleton"] = True
        out["singletonImplicit"] = True
    else:
        out["singleton"] = bool(c.get("singleton", False))
        if out["singleton"]:
            for k in ("cut", "maxLen"):
                if k in c:
                    raise ValueError(f"Collection '{cname}': '{k}' has no meaning on a singleton collection")
        else:
            out["cut"] = c.get("cut", "")
            if "maxLen" in c:
                out["maxLen"] = _checkMaxLen(cname, c["maxLen"])
    return out


## Every key a seeding block may carry
SEEDING_REQUIRED = {"beamSpot", "primaryVertices", "goodPv", "ptAbove", "nSigmaDxyBsAbove", "minPixelLayers", "minStripLayers", "maxFirstPixelLayer"}
SEEDING_FIELDS = SEEDING_REQUIRED | {"trackErrScale", "trackDrop"}
TRACK_DROP_FIELDS = {"coefficient", "absDxyBsCap"}

## The three uncertainty curves trackErrScale holds for each detector region, and the scale that leaves a track unchanged
TRACK_ERR_PARTS = ("dxy", "dsz", "dxyDsz")
NO_TRACK_ERR_SCALE = {"barrelAbsEtaBelow": 0.0, **{region: {part: {"form": "none", "p": []} for part in TRACK_ERR_PARTS} for region in ("barrel", "endcap")}}


def _resolveSeeding(cname, seeding, era, isMC):
    if not isinstance(seeding, dict):
        raise ValueError(f"Collection '{cname}': a seedTrack collection needs a 'seeding' block")
    unknown = sorted(set(seeding) - SEEDING_FIELDS)
    if unknown:
        raise ValueError(f"Collection '{cname}': seeding has unknown key(s) {unknown}; valid keys are {sorted(SEEDING_FIELDS)}")
    missing = sorted(SEEDING_REQUIRED - set(seeding))
    if missing:
        raise ValueError(f"Collection '{cname}': seeding is missing {missing}")

    out = {k: seeding[k] for k in sorted(SEEDING_REQUIRED)}
    out["trackErrScale"] = NO_TRACK_ERR_SCALE
    if isMC and "trackErrScale" in seeding:
        scale = _forEra(cname, "trackErrScale", seeding["trackErrScale"], era)
        for region in ("barrel", "endcap"):
            if set(scale.get(region, {})) != set(TRACK_ERR_PARTS):
                raise ValueError(f"Collection '{cname}': trackErrScale.{era}.{region} needs exactly {list(TRACK_ERR_PARTS)}")
        out["trackErrScale"] = scale
    out["trackDrop"] = {"coefficient": 0.0, "absDxyBsCap": 0.0}
    if isMC and "trackDrop" in seeding:
        drop = seeding["trackDrop"]
        if set(drop) != TRACK_DROP_FIELDS:
            raise ValueError(f"Collection '{cname}': trackDrop needs exactly {sorted(TRACK_DROP_FIELDS)}")
        coefficient = drop["coefficient"]
        out["trackDrop"] = {"coefficient": _forEra(cname, "trackDrop.coefficient", coefficient, era) if isinstance(coefficient, dict) else coefficient, "absDxyBsCap": drop["absDxyBsCap"]}
    return out


## Every key the JECs may carry
JEC_FIELDS = {"payload", "primaryVertices", "levels"}


def _checkJec(cname, jec):
    if not isinstance(jec, dict):
        raise ValueError(f"Collection '{cname}': a vertexJet collection needs a 'jec' block")
    unknown = sorted(set(jec) - JEC_FIELDS)
    if unknown:
        raise ValueError(f"Collection '{cname}': jec has unknown key(s) {unknown}; valid keys are {sorted(JEC_FIELDS)}")
    missing = sorted(JEC_FIELDS - set(jec))
    if missing:
        raise ValueError(f"Collection '{cname}': jec is missing {missing}")
    if not jec["levels"]:
        raise ValueError(f"Collection '{cname}': jec names no correction levels")
    return {"payload": jec["payload"], "primaryVertices": jec["primaryVertices"], "levels": list(jec["levels"])}


def _jetVariableExprs(era):
    """The expressions behind the Jet collection's variables, which a vertexJet requirement names."""
    jets = loadWithIncludes("jets", contentDirs(era))
    return {name: v["expr"] for name, v in jets["collections"]["Jet"]["variables"].items()}


## Every key the vertexing blocks may carry
VERTEXING_FIELDS = {"beamSpot", "jets", "minTracks", "maxChi2PerDof", "kalman", "sharedTracks", "zRefit", "mergeNearby", "sharedJets", "beampipe"}
VERTEXING_BLOCKS = {
    "kalman":       {"maxDistance", "maxIterations", "smoothing"},
    "sharedTracks": {"mergeBelowSigma", "keepBelowSigma", "tieBelowSigma"},
    "zRefit":       {"maxShiftSigma"},
    "mergeNearby":  {"deltaPhiBelow", "distance2dBelow", "dbvAbove"},
    "sharedJets":   {"maxDeltaPhi"},
    "beampipe":     {"radius", "dataCenter", "mcCenter"},
}


def _checkVertexing(cname, vertexing, era, isMC):
    """The vertexer parameters, with every block complete and the beampipe resolved for this era."""
    if not isinstance(vertexing, dict):
        raise ValueError(f"Collection '{cname}': a dv collection needs a 'vertexing' block")
    unknown = sorted(set(vertexing) - VERTEXING_FIELDS)
    if unknown:
        raise ValueError(f"Collection '{cname}': vertexing has unknown key(s) {unknown}; valid keys are {sorted(VERTEXING_FIELDS)}")
    missing = sorted(VERTEXING_FIELDS - set(vertexing))
    if missing:
        raise ValueError(f"Collection '{cname}': vertexing is missing {missing}")
    for block, fields in VERTEXING_BLOCKS.items():
        unknown = sorted(set(vertexing[block]) - fields)
        if unknown:
            raise ValueError(f"Collection '{cname}': vertexing.{block} has unknown key(s) {unknown}; valid keys are {sorted(fields)}")
        missing = sorted(fields - set(vertexing[block]))
        if missing:
            raise ValueError(f"Collection '{cname}': vertexing.{block} is missing {missing}")
    beampipe = vertexing["beampipe"]
    center = beampipe["mcCenter"] if isMC else _forEra(cname, "beampipe.dataCenter", beampipe["dataCenter"], era)
    return dict(vertexing, beampipe={"radius": _forEra(cname, "beampipe.radius", beampipe["radius"], era), "center": center})


def _forEra(cname, key, byEra, era):
    if era not in byEra:
        raise ValueError(f"Collection '{cname}': '{key}' defines no entry for era '{era}'; it defines {sorted(byEra)}")
    return byEra[era]


def _checkMaxLen(cname, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Collection '{cname}': maxLen must be an integer, got {value!r}")
    if not 1 <= value <= 100000:
        raise ValueError(f"Collection '{cname}': maxLen must be between 1 and 100000, got {value}")
    return value


def _checkVars(cname, variables):
    if not variables:
        raise ValueError(f"Collection '{cname}': no variables defined")
    out = {}
    for vname, v in variables.items():
        unknown = sorted(set(v) - VARIABLE_FIELDS)
        if unknown:
            raise ValueError(f"{cname}.{vname}: unknown key(s) {unknown}; valid keys are {sorted(VARIABLE_FIELDS)}")
        if "expr" not in v:
            raise ValueError(f"{cname}.{vname}: missing 'expr'")
        vtype = v.get("type", "float")
        if vtype not in VALID_TYPES:
            raise ValueError(f"{cname}.{vname}: bad type '{vtype}' (allowed: {sorted(VALID_TYPES)})")
        entry = {"expr": v["expr"], "type": vtype, "doc": v.get("doc", "")}
        if "precision" in v:
            p = v["precision"]
            if isinstance(p, bool) or not isinstance(p, int) or not (p == -1 or 0 <= p <= 32):
                raise ValueError(f"{cname}.{vname}: precision must be -1 for full precision, or an integer between 0 and 32, got {p!r}")
            entry["precision"] = p
        out[vname] = entry
    return out


def _checkExtVars(cname, variables):
    if not variables:
        raise ValueError(f"Collection '{cname}': no variables defined")
    out = {}
    for vname, v in variables.items():
        unknown = sorted(set(v) - EXTVAR_FIELDS)
        if unknown:
            raise ValueError(f"{cname}.{vname}: unknown key(s) {unknown}; valid keys are {sorted(EXTVAR_FIELDS)}")
        if "src" not in v:
            raise ValueError(f"{cname}.{vname}: 'global' variables need 'src' (an InputTag)")
        vtype = v.get("type", "double")
        if vtype not in VALID_TYPES:
            raise ValueError(f"{cname}.{vname}: bad type '{vtype}'")
        out[vname] = {"src": v["src"], "type": vtype, "doc": v.get("doc", "")}
    return out


def summarize(resolved, counts=None):
    """One line per collection, as `kamui content <name>` prints it. counts, when given, replaces a collection's variable count with the number of branches it writes."""
    lines = ["  " + " ".join([f"{'Collection':<12}", f"{'Type':<16}", f"{'Source':<34}", f"{'Vars':>4}"])]
    for cname, c in sorted(resolved["collections"].items()):
        n = (counts or {}).get(cname, len(c.get("variables", c.get("extVariables", {}))))
        bits = [f"{cname:<12}", f"{c['kind']:<16}", f"{c.get('src',''):<34}"]
        bits.append(f"{n:>4}")
        if c.get("cut"):
            bits.append(f"cut='{c['cut']}'")
        if c.get("maxLen"):
            bits.append(f"maxLen={c['maxLen']}")
        lines.append("  " + " ".join(bits))
    return "\n".join(lines)


def listTriggerConfigs():
    """Names of the trigger configs available, each with its run folder, such as run2/lepton."""
    runs = [r for r in RUNS if os.path.isdir(os.path.join(paths.TRIGGERS_DIR, r))]
    return sorted(f"{r}/{f[:-5]}" for r in runs for f in os.listdir(os.path.join(paths.TRIGGERS_DIR, r)) if f.endswith(".json"))


def validateTriggers(erasByRun):
    """Check every trigger config loads through loadTriggerConfig from its own run folder, for each era it keys its paths by, and that each of those eras is one of its run's eras in erasByRun. Returns a list of problems, one per broken file, empty if all are fine."""
    problems = []
    for label in listTriggerConfigs():
        run, name = label.split("/", 1)
        triggerDir = os.path.join(paths.TRIGGERS_DIR, run)
        try:
            eras = triggerEras(name, triggerDir)
            stray = [e for e in eras if e not in erasByRun.get(run, [])]
            if stray:
                raise ValueError(f"Trigger config '{label}' keys paths by {', '.join(stray)}, outside the {run} eras {', '.join(erasByRun.get(run, []))}")
            for era in eras or [None]:
                loadTriggerConfig(name, era, triggerDir)
        except Exception as e:
            problems.append(str(e))
    return problems
