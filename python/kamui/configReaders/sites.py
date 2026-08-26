"""
Reads sites.json: where things are stored, which release to use, which site to stage out to.
"""

# Import Block

## Standard Python imports
import json
import os

## Kamui modules
from ..foundations import paths
from ..foundations.config import stripComments


def _expand(value, where):
    """Expand $USER and friends in config strings, recursively."""
    if isinstance(value, str):
        out = os.path.expandvars(value)
        if "$" in out:
            raise ValueError(f"sites.json: {where} still contains an unset variable after expansion: {out!r}")
        return out
    if isinstance(value, dict):
        return {k: _expand(v, f"{where}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v, where) for v in value]
    return value


def loadSites(path=None):
    """Load config/sites.json, expanding environment variables."""
    with open(path or paths.SITES_FILE) as f:
        cfg = stripComments(json.load(f))
    return {k: _expand(v, k) for k, v in cfg.items()}
