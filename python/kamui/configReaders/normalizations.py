"""
Reads the normalization configs: the luminosity per era, the cross section files, and the generator sums that norm records.
"""

# Import Block

## Standard Python imports
import os

## Kamui modules
from ..foundations import paths
from ..foundations.config import RUNS, loadJson

## Every top-level key lumi.json may carry, and the keys of one luminosity entry
LUMI_FIELDS = {"eras", "channels"}
LUMI_ENTRY_FIELDS = {"lumi", "source"}

## Every key one run block of a cross section file may carry, and the keys of one process and of one filter efficiency
XSEC_RUN_FIELDS = {"processes", "filterEfficiencies"}
PROCESS_FIELDS = {"xsec", "source"}
FILTER_FIELDS = {"byScalarMass", "source"}

## Every number norm may record for one sample
SUM_FIELDS = {"genEvents", "sumGenWeight", "sumGenWeight2"}


def validateNormalizations():
    """Load every file under config/normalizations/ and check its format. Returns a list of problems, empty if all are fine."""
    problems = []
    for f in sorted(x for x in os.listdir(paths.NORM_DIR) if x.endswith(".json")):
        path = os.path.join(paths.NORM_DIR, f)
        try:
            cfg = loadJson(path)
        except ValueError as e:
            problems.append(str(e))
            continue
        if not isinstance(cfg, dict):
            problems.append(f"{path}: the top level must be an object")
            continue
        if path == paths.LUMI_FILE:
            check = _checkLumi
        elif path == paths.GENERATOR_SUMS_FILE:
            check = _checkSums
        else:
            check = _checkCrossSections
        try:
            check(cfg)
        except ValueError as e:
            problems.append(f"{path}: {e}")
    return problems


def _isNumber(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _checkEntry(where, entry, fields, number):
    """One entry holding exactly the given keys, with a positive number under `number` and a non-empty source."""
    if not isinstance(entry, dict) or set(entry) != fields:
        raise ValueError(f"{where} must be an object with exactly {sorted(fields)}")
    if not _isNumber(entry[number]) or entry[number] <= 0:
        raise ValueError(f"{where} has {number} {entry[number]!r}; it must be a positive number")
    if not isinstance(entry["source"], str) or not entry["source"]:
        raise ValueError(f"{where} needs a 'source' saying where the number came from")


def _checkLumi(cfg):
    bad = sorted(set(cfg) - LUMI_FIELDS)
    if bad:
        raise ValueError(f"unknown key(s) {bad}; valid keys are {sorted(LUMI_FIELDS)}")
    eras = cfg.get("eras")
    if not isinstance(eras, dict) or not eras:
        raise ValueError("needs 'eras', the luminosity of each era")
    for era, entry in eras.items():
        _checkEntry(f"eras.{era}", entry, LUMI_ENTRY_FIELDS, "lumi")
    channels = cfg.get("channels", {})
    if not isinstance(channels, dict):
        raise ValueError("'channels' must be an object keyed by channel")
    for channel, byEra in channels.items():
        if not isinstance(byEra, dict) or not byEra:
            raise ValueError(f"channels.{channel} must be an object keyed by era")
        for era, entry in byEra.items():
            if era not in eras:
                raise ValueError(f"channels.{channel} overrides era '{era}', which 'eras' does not list")
            _checkEntry(f"channels.{channel}.{era}", entry, LUMI_ENTRY_FIELDS, "lumi")


def _checkCrossSections(cfg):
    """A cross section file holds one block per run, so a sample is only ever normalized by numbers for its own run."""
    if not cfg:
        raise ValueError(f"holds no run block; give one under {' or '.join(RUNS)}")
    bad = sorted(set(cfg) - set(RUNS))
    if bad:
        raise ValueError(f"top-level key(s) {bad} name no run; valid keys are {list(RUNS)}")
    for run, block in cfg.items():
        if not isinstance(block, dict):
            raise ValueError(f"{run} must be an object")
        bad = sorted(set(block) - XSEC_RUN_FIELDS)
        if bad:
            raise ValueError(f"{run} has unknown key(s) {bad}; valid keys are {sorted(XSEC_RUN_FIELDS)}")
        processes = block.get("processes")
        if not isinstance(processes, dict) or not processes:
            raise ValueError(f"{run} needs 'processes', the cross section of each process")
        for process, entry in processes.items():
            _checkEntry(f"{run}.processes.{process}", entry, PROCESS_FIELDS, "xsec")
        filters = block.get("filterEfficiencies", {})
        if not isinstance(filters, dict):
            raise ValueError(f"{run}.filterEfficiencies must be an object")
        for key, entry in filters.items():
            where = f"{run}.filterEfficiencies.{key}"
            if not isinstance(entry, dict) or set(entry) != FILTER_FIELDS:
                raise ValueError(f"{where} must be an object with exactly {sorted(FILTER_FIELDS)}")
            byMass = entry["byScalarMass"]
            if not isinstance(byMass, dict) or not byMass or not all(_isNumber(v) and 0 < v <= 1 for v in byMass.values()):
                raise ValueError(f"{where}.byScalarMass must map each scalar mass to an efficiency between 0 and 1")
            if not isinstance(entry["source"], str) or not entry["source"]:
                raise ValueError(f"{where} needs a 'source' saying where the numbers came from")


def _checkSums(cfg):
    if set(cfg) != {"samples"} or not isinstance(cfg["samples"], dict):
        raise ValueError("must hold only 'samples', an object keyed by sample name")
    for name, entry in cfg["samples"].items():
        if not isinstance(entry, dict):
            raise ValueError(f"samples.{name} must be an object")
        bad = sorted(set(entry) - SUM_FIELDS)
        if bad:
            raise ValueError(f"samples.{name} has unknown key(s) {bad}; valid keys are {sorted(SUM_FIELDS)}")
        if "genEvents" in entry and (isinstance(entry["genEvents"], bool) or not isinstance(entry["genEvents"], int) or entry["genEvents"] < 0):
            raise ValueError(f"samples.{name} has genEvents {entry['genEvents']!r}; it must be a whole number")
        for key in ("sumGenWeight", "sumGenWeight2"):
            if key in entry and not _isNumber(entry[key]):
                raise ValueError(f"samples.{name} has {key} {entry[key]!r}; it must be a number")
