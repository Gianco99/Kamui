#!/usr/bin/env python3
"""
Count how many events pass a channel's trigger OR, per sample, per path.

This is the number we compare against JMTucker.

Needs cmsenv (uses ROOT). No grid proxy needed for files already on our EOS.

  python3 tools/triggerYields.py --task run2val
  python3 tools/triggerYields.py --files out.root --triggers run2Lepton
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))
from kamui.foundations import paths                                        # noqa: E402
from kamui.configReaders.catalog import loadCatalog  # noqa: E402
from kamui.foundations.config import loadWithIncludes                      # noqa: E402
from kamui.configReaders.content import resolveContent                       # noqa: E402
from kamui.configReaders.sites import loadSites                      # noqa: E402


def branchName(path):
    """'HLT_IsoMu24_v*' -> 'HLT_IsoMu24'. The output module names branches without the version."""
    return path.split("_v*")[0].rstrip("*").rstrip("_")


def listEos(sites, lfnDir):
    red = sites["eosRedirector"].rstrip("/")
    r = subprocess.run(["xrdfs", red, "ls", lfnDir], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [f"{red}/{l.strip()}" for l in r.stdout.splitlines() if l.strip().endswith(".root")]


def yieldsFor(files, paths_):
    """Return (nTotal, nPass, {path: nFires}, nPassAfterVeto)."""
    import ROOT

    # TChain.Add silently accepts a path that does not exist, which would otherwise
    # surface as a believable-looking zero yield. Check each file first.
    chain = ROOT.TChain("Events")
    good, dead = [], []
    for f in files:
        try:                              # newer ROOT raises instead of returning null
            tf = ROOT.TFile.Open(f)
        except OSError:
            tf = None
        if tf and not tf.IsZombie() and tf.Get("Events"):
            good.append(f)
            chain.Add(f)
        else:
            dead.append(f)
        if tf:
            tf.Close()
    if dead:
        print(f"  WARNING: {len(dead)} of {len(files)} file(s) unreadable or have no Events tree, e.g. {dead[0]}")
    if not good:
        return 0, 0, {}
    total = chain.GetEntries()
    if total == 0:
        return 0, 0, {}

    have = {b.GetName() for b in chain.GetListOfBranches()}
    perPath, terms = {}, []
    for p in paths_:
        b = branchName(p)
        if b not in have:
            perPath[b] = None                      # not in this file's menu at all
            continue
        perPath[b] = chain.GetEntries(b)
        terms.append(b)

    if not terms:
        return total, 0, perPath
    orExpr = "||".join(terms)
    nPass = chain.GetEntries(orExpr)

    return total, nPass, perPath


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", help="Task name under ntupleProduction/jobs/")
    ap.add_argument("--files", nargs="+", help="Explicit ntuple files, in place of a task")
    ap.add_argument("--triggers", help="Trigger config name; required with --files")
    ap.add_argument("--sample", action="append", help="Restrict to these samples")
    ap.add_argument("--perPath", action="store_true", help="Print the per-path breakdown")
    args = ap.parse_args()

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kError

    jobs = []
    if args.files:
        if not args.triggers:
            sys.exit("--files needs --triggers <name>")
        trig = loadWithIncludes(args.triggers, paths.TRIGGERS_DIR)
        jobs.append(("(files)", args.triggers, trig["paths"], args.files, None))
    else:
        if not args.task:
            sys.exit("give --task or --files")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", args.task):
            sys.exit(f"bad task name {args.task!r}")
        rec = os.path.join(paths.JOBS_DIR, args.task, "task.json")
        if not os.path.exists(rec):
            sys.exit(f"no task '{args.task}' under {paths.JOBS_DIR}")
        with open(rec) as f:
            info = json.load(f)
        sites = loadSites()
        catalog = {s["name"]: s for s in loadCatalog()}
        wanted = args.sample or info["samples"]
        for name in wanted:
            s = catalog.get(name)
            if s is None:
                print(f"  {name}: not in the catalog any more, skipping")
                continue
            skim = resolveContent(s["content"], isMC=bool(s["isMC"]), era=s["era"])["skim"]
            if not skim.get("hltPaths"):
                print(f"  {name}: content preset '{s['content']}' declares no trigger skim, skipping")
                continue
            files = listEos(sites, f"{info.get('outLFNDirBase') or info['outDirBase']}/{name}")
            jobs.append((name, skim.get("triggers", "?"), skim["hltPaths"],
                         files, s.get("notes", "")))

    hdr = f"{'sample':<42} {'channel':<16} {'files':>5} {'total':>9} {'pass':>9} {'eff':>8}"
    print(hdr)
    print("-" * len(hdr))

    for name, chan, plist, files, notes in jobs:
        if not files:
            print(f"{name:<42} {chan:<16} {'0':>5}   no output files found")
            continue
        total, nPass, perPath = yieldsFor(files, plist)
        eff = 100.0 * nPass / total if total else 0.0
        line = f"{name:<42} {chan:<16} {len(files):>5} {total:>9,} {nPass:>9,} {eff:>7.3f}%"
        print(line)
        if notes:
            print(f"{'':<42} JMTucker reference: {notes}")
        if args.perPath:
            for b, n in sorted(perPath.items()):
                mark = "not in menu" if n is None else f"{n:,}"
                print(f"{'':<44} {b:<58} {mark:>12}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
