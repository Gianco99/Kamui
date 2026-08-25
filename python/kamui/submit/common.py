"""
Shared job-area machinery for both backends.

Every submission writes a self-contained directory under SamplesFromDAS/jobs/:

    jobs/<task>/
      task.json               what was submitted, so a task is reproducible
      <preset>.resolved.json  the flattened content config the cmsRun cfg reads
      <backend files>

That directory is the single source of truth for a production. Nothing is
hidden in a shell history or in someone's terminal.
"""

import json
import os

from ..foundations import paths
from ..configReaders.content import resolveContent


def taskDir(taskName, create=True):
    d = os.path.join(paths.JOBS_DIR, taskName)
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def writeResolvedContent(d, presetName, isMC):
    """Flatten a content preset into the job area and return its path."""
    resolved = resolveContent(presetName, isMC=isMC)
    suffix = "mc" if isMC else "data"
    out = os.path.join(d, f"{presetName}.{suffix}.json")
    with open(out, "w") as f:
        json.dump(resolved, f, indent=2)
    return out


def writeTaskRecord(d, record):
    with open(os.path.join(d, "task.json"), "w") as f:
        json.dump(record, f, indent=2)


def outputPath(sites, taskName, sampleName):
    """EOS directory a sample's ntuples land in."""
    return "/".join([sites["stageoutBase"].rstrip("/"), "ntuples", taskName, sampleName])


def chunk(items, n):
    """Split `items` into lists of at most n entries."""
    return [items[i:i + n] for i in range(0, len(items), n)]
