"""
Turns a content config into a form the cmsRun config consumes.
The file format is documented in config/content/README.txt, and its details in the CLAUDE.md beside it.
"""

# Import Block

## Standard Python imports
import os

## Kamui modules
from ..foundations import paths
from ..foundations.config import loadWithIncludes
from .slimming import buildOutputCommands

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
}

# Kinds whose producer takes no `src`/`cut`/`variables`
FIXED_CONTENT_KINDS = {"pileup", "genWeight"}
# Kinds that are inherently one-per-event
ALWAYS_SINGLETON_KINDS = {"beamSpot", "genEvent"}
# `global` uses externalVariables-style entries (src/type/doc) instead of expr.
EXTVAR_KINDS = {"global"}

VALID_TYPES = {"float", "double", "int", "uint", "int16", "uint16", "uint8", "bool"}


def listPresets(contentDir=None):
    """Every content config, grouped by the subdirectory it lives in. Returns {group: [names]}."""
    contentDir = contentDir or paths.CONTENT_DIR
    out = {}
    for d in sorted(os.listdir(contentDir)):
        full = os.path.join(contentDir, d)
        if os.path.isdir(full):
            out[d] = sorted(f[:-5] for f in os.listdir(full) if f.endswith(".json"))
    loose = sorted(f[:-5] for f in os.listdir(contentDir) if f.endswith(".json"))
    if loose:
        out[""] = loose
    return out


## Every top-level key a content config may carry
CONTENT_FIELDS = {"collections", "triggerBits", "skim", "miniaod"}


def resolveContent(name, contentDir=None, isMC=True):
    """Flatten a preset's include chain and translate it into what a job receives: name, isMC, collections, triggerBits, skim, miniaod."""
    contentDir = contentDir or paths.CONTENT_DIR
    cfg = loadWithIncludes(name, contentDir)

    unknown = sorted(set(cfg) - CONTENT_FIELDS)
    if unknown:
        raise ValueError(f"content config '{name}' has unknown key(s) {unknown}; valid keys are {sorted(CONTENT_FIELDS)}")
    if not cfg.get("collections"):
        raise ValueError(f"content config '{name}' defines no collections; check the spelling of 'include'")

    collections = {}
    for cname, c in cfg.get("collections", {}).items():
        if not isinstance(c, dict):
            raise ValueError(f"content config '{name}': collection '{cname}' must be an object, got {type(c).__name__}")
        if c.get("drop"):                       # an including config can delete an inherited collection
            if "type" not in c:
                raise ValueError(f"content config '{name}': collection '{cname}' is dropped but never defined; check the spelling")
            continue
        if c.get("mcOnly") and not isMC:
            continue
        if c.get("dataOnly") and isMC:
            continue
        collections[cname] = _translate(cname, c)

    return {
        "name":        name,
        "isMC":        isMC,
        "collections": collections,
        "triggerBits": cfg.get("triggerBits", {}),
        "skim":        _resolveSkim(cfg.get("skim", {})),
        "miniaod":     _resolveMiniaod(cfg.get("miniaod", {}), isMC),
    }


## Every key a miniaod block may carry
MINIAOD_FIELDS = {"keep", "keepExtra", "drop"}


def _resolveMiniaod(cfg, isMC):
    """Expand the optional slimmed-MiniAOD block into EDM outputCommands."""
    if not cfg:
        return {}
    if not isinstance(cfg, dict):
        raise ValueError(f"miniaod block must be an object, got {type(cfg).__name__}")
    unknown = sorted(set(cfg) - MINIAOD_FIELDS)
    if unknown:
        raise ValueError(f"miniaod block has unknown key(s) {unknown}; valid keys are {sorted(MINIAOD_FIELDS)}")
    return {
        "keep":           cfg.get("keep", []),
        "outputCommands": buildOutputCommands(cfg, isMC=isMC),
    }


## Every key a skim block may carry
SKIM_FIELDS = {"triggers", "mode", "process"}


def _resolveSkim(skim):
    """
    Expand a skim block.
    """
    if not skim:
        return {}
    unknown = sorted(set(skim) - SKIM_FIELDS)
    if unknown:
        raise ValueError(f"skim has unknown key(s) {unknown}; valid keys are {sorted(SKIM_FIELDS)}")
    name = skim.get("triggers")
    if not name:
        return {}
    trig = loadWithIncludes(name, paths.TRIGGERS_DIR)
    if "paths" not in trig:
        raise ValueError(f"trigger config '{name}' defines no 'paths'")
    out = dict(skim)
    mode = skim.get("mode", trig.get("mode", "any"))
    if mode not in ("any", "all"):
        raise ValueError(f"skim mode '{mode}' is not 'any' or 'all'")
    out.update({
        "triggers":  name,
        "hltPaths":  trig["paths"],
        "mode":      mode,
        "process":   skim.get("process", trig.get("process", "HLT")),
    })
    return out


## Every key a collection may carry
COLLECTION_FIELDS = {"type", "src", "doc", "cut", "maxLen", "variables", "params", "singleton", "extension", "mcOnly", "dataOnly", "drop"}
VARIABLE_FIELDS = {"expr", "type", "doc", "precision"}
EXTVAR_FIELDS = {"src", "type", "doc"}


def _translate(cname, c):
    unknown = sorted(set(c) - COLLECTION_FIELDS)
    if unknown:
        raise ValueError(f"collection '{cname}' has unknown key(s) {unknown}; valid keys are {sorted(COLLECTION_FIELDS)}")
    kind = c.get("type")
    if kind not in KIND_TO_PLUGIN:
        raise ValueError(
            f"collection '{cname}': unknown type '{kind}'. "
            f"Known types: {', '.join(sorted(KIND_TO_PLUGIN))}"
        )

    out = {
        "plugin":    KIND_TO_PLUGIN[kind],
        "kind":      kind,
        "doc":       c.get("doc", ""),
        "extension": bool(c.get("extension", False)),
    }
    if kind in FIXED_CONTENT_KINDS:
        out["params"] = c.get("params", {})
        if "src" in c:
            out["src"] = c["src"]
        return out

    if kind in EXTVAR_KINDS:
        for k in ("cut", "maxLen", "singleton"):
            if k in c:
                raise ValueError(f"collection '{cname}': '{k}' has no meaning on a '{kind}' collection")
        out["extVariables"] = _checkExtVars(cname, c.get("variables", {}))
        return out

    if "src" not in c:
        raise ValueError(f"collection '{cname}': missing 'src'")
    out["src"] = c["src"]

    out["variables"] = _checkVars(cname, c.get("variables", {}))
    if kind in ALWAYS_SINGLETON_KINDS:
        for k in ("cut", "maxLen"):
            if k in c:
                raise ValueError(f"collection '{cname}': '{k}' has no meaning on a singleton collection")
        # These plugins are one-per-event by construction and reject a `singleton` parameter
        out["singleton"] = True
        out["singletonImplicit"] = True
    else:
        out["singleton"] = bool(c.get("singleton", False))
        if out["singleton"]:
            for k in ("cut", "maxLen"):
                if k in c:
                    raise ValueError(f"collection '{cname}': '{k}' has no meaning on a singleton collection")
        else:
            out["cut"] = c.get("cut", "")
            if "maxLen" in c:
                out["maxLen"] = _checkMaxLen(cname, c["maxLen"])
    return out


def _checkMaxLen(cname, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"collection '{cname}': maxLen must be an integer, got {value!r}")
    if not 1 <= value <= 100000:
        raise ValueError(f"collection '{cname}': maxLen must be between 1 and 100000, got {value}")
    return value


def _checkVars(cname, variables):
    if not variables:
        raise ValueError(f"collection '{cname}': no variables defined")
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
        raise ValueError(f"collection '{cname}': no variables defined")
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
    """One line per collection - what `kamui content <name>` prints."""
    lines = []
    for cname, c in sorted(resolved["collections"].items()):
        n = len(c.get("variables", c.get("extVariables", {})))
        bits = [f"{cname:<12}", f"{c['kind']:<16}", f"{c.get('src',''):<34}"]
        bits.append(f"{n:>3} vars")
        if c.get("cut"):
            bits.append(f"cut='{c['cut']}'")
        if c.get("maxLen"):
            bits.append(f"maxLen={c['maxLen']}")
        lines.append("  " + " ".join(bits))
    return "\n".join(lines)


def validateTriggers():
    """Check every trigger config parses and declares paths. Returns a list of problems, empty if all are fine."""
    problems = []
    for f in sorted(x for x in os.listdir(paths.TRIGGERS_DIR) if x.endswith(".json")):
        try:
            trig = loadWithIncludes(f[:-5], paths.TRIGGERS_DIR)
        except Exception as e:
            problems.append(f"trigger config '{f}': {e}")
            continue
        if not trig.get("paths"):
            problems.append(f"trigger config '{f}' declares no paths")
    return problems
