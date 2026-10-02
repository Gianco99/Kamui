"""
Turns a content config into a form the cmsRun config consumes. The file format is documented in config/content/README.md.
"""

# Import Block

## Standard Python imports
import os

## Kamui modules
from ..foundations import paths
from ..foundations.config import RUNS, eraGroup, loadJson, loadWithIncludes, runDir
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
        "triggerBits": cfg.get("triggerBits", {}),
        "skim":        _resolveSkim(cfg.get("skim", {}), era),
    }


## Every key a skim block may carry
SKIM_FIELDS = {"triggers", "mode", "process"}


def loadTriggerPaths(name, era=None):
    """The HLT path patterns a trigger config defines, read from the era's run folder."""
    trig = loadWithIncludes(name, runDir(paths.TRIGGERS_DIR, era))
    if "paths" not in trig:
        raise ValueError(f"Trigger config '{name}' defines no 'paths'")
    return list(trig["paths"])


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
    trig = loadWithIncludes(name, runDir(paths.TRIGGERS_DIR, era))
    if "paths" not in trig:
        raise ValueError(f"Trigger config '{name}' defines no 'paths'")
    out = dict(skim)
    mode = skim.get("mode", trig.get("mode", "any"))
    if mode not in ("any", "all"):
        raise ValueError(f"Skim mode '{mode}' is not 'any' or 'all'")
    out.update({
        "triggers":  name,
        "hltPaths":  trig["paths"],
        "mode":      mode,
        "process":   skim.get("process", trig.get("process", "HLT")),
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
        out["vertexing"] = _checkVertexing(cname, c.get("vertexing"))
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
SEEDING_FIELDS = SEEDING_REQUIRED | {"dxyErrScale", "trackDrop"}
TRACK_DROP_FIELDS = {"coefficient", "absDxyBsCap"}


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
    out["dxyErrScale"] = {"form": "none", "barrelAbsEtaBelow": 0.0, "barrel": [], "endcap": []}
    if isMC and "dxyErrScale" in seeding:
        out["dxyErrScale"] = _forEra(cname, "dxyErrScale", seeding["dxyErrScale"], era)
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
VERTEXING_FIELDS = {"beamSpot", "jets", "minTracks", "maxChi2PerDof", "kalman", "sharedTracks", "zRefit", "mergeNearby", "sharedJets"}
VERTEXING_BLOCKS = {
    "kalman":       {"maxDistance", "maxIterations", "smoothing"},
    "sharedTracks": {"mergeBelowSigma", "keepBelowSigma", "tieBelowSigma"},
    "zRefit":       {"maxShiftSigma"},
    "mergeNearby":  {"deltaPhiBelow", "distance2dBelow", "dbvAbove"},
    "sharedJets":   {"maxDeltaPhi"},
}


def _checkVertexing(cname, vertexing):
    """The vertexer parameters, with every block complete."""
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
    return vertexing


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


def summarize(resolved):
    """One line per collection, as `kamui content <name>` prints it."""
    lines = ["  " + " ".join([f"{'Collection':<12}", f"{'Type':<16}", f"{'Source':<34}", f"{'Vars':>4}"])]
    for cname, c in sorted(resolved["collections"].items()):
        n = len(c.get("variables", c.get("extVariables", {})))
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


def validateTriggers():
    """Check every trigger config parses and declares paths. Returns a list of problems, empty if all are fine."""
    problems = []
    for name in listTriggerConfigs():
        try:
            trig = loadWithIncludes(name, paths.TRIGGERS_DIR)
        except Exception as e:
            problems.append(f"Trigger config '{name}': {e}")
            continue
        if not trig.get("paths"):
            problems.append(f"Trigger config '{name}' declares no paths")
    return problems


## Collections that are meant to differ between the two era sets
ERA_SPECIFIC_COLLECTIONS = {"leptons", "jets", "vertexing"}


def validateEraCopies(contentDir=None):
    """Each era carries its own copy of every collection. Report copies that drifted, or era-specific ones that did not."""
    contentDir = contentDir or paths.CONTENT_DIR
    problems = []
    colls = listCollections(contentDir)
    if set(colls) != {"run2", "run3"}:
        return [f"Expected content sets run2 and run3, found {sorted(colls)}"]
    for name in sorted(set(colls["run2"]) | set(colls["run3"])):
        a = os.path.join(contentDir, "run2", "collections", name + ".json")
        b = os.path.join(contentDir, "run3", "collections", name + ".json")
        if not (os.path.exists(a) and os.path.exists(b)):
            problems.append(f"Collection '{name}' exists in only one era set")
            continue
        same = loadJson(a) == loadJson(b)
        if name in ERA_SPECIFIC_COLLECTIONS and same:
            problems.append(f"Collection '{name}' is meant to differ by era but both copies are identical")
        if name not in ERA_SPECIFIC_COLLECTIONS and not same:
            problems.append(f"Collection '{name}' differs between run2 and run3; add it to ERA_SPECIFIC_COLLECTIONS if deliberate, otherwise the copies have drifted")
    return problems
