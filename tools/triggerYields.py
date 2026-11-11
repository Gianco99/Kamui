#!/usr/bin/env python3
"""
Count how many events pass a channel's trigger, per sample, per path. The paths combine as the trigger config's mode says: any is an OR, all an AND.

This is the number we compare against JMTucker.

Needs cmsenv (uses ROOT) and no grid proxy for files already on our EOS.

  python3 tools/triggerYields.py --task run2Val
  python3 tools/triggerYields.py --files out.root --triggers run2/lepton
  python3 tools/triggerYields.py --files out.root --triggers run3/bParking --era Summer24
"""

# Import Block

## Standard Python imports
import argparse
import json
import os
import re
import subprocess
import sys

## Kamui modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))
from kamui.foundations import paths
from kamui.select.io import findInputs
from kamui.configReaders.content import loadTriggerConfig, triggerEras


def branchName(path):
    """'HLT_IsoMu24_v*' -> 'HLT_IsoMu24'. The output module names branches without the version."""
    return path.split("_v*")[0].rstrip("*").rstrip("_")


def taskSkim(info, detail):
    """The skim a task's jobs applied to one sample, read from the resolved content saved in its task.json, or None when the record holds none for that sample."""
    written = {k: c for k, c in (info.get("resolvedContent") or {}).items() if c.get("name") == detail["content"] and bool(c.get("isMC")) == bool(detail["isMC"])}
    # A preset resolved for several eras is saved once per era, as <preset>.<mc or data>.<era>.json
    written = {k: c for k, c in written.items() if k.endswith(f".{detail['era']}.json")} or written
    if len(written) != 1:
        return None
    return next(iter(written.values())).get("skim") or {}


def yieldsFor(files, paths_, mode):
    """Return (nTotal, nPass, {path: nFires}). Under mode any an event passes when one path fired, and under mode all when every path in the file's menu fired."""
    import ROOT

    # TChain.Add silently accepts a missing path, which would surface as a believable zero yield.
    chain = ROOT.TChain("Events")
    good, dead = [], []
    for f in files:
        try:  # TFile.Open raises OSError on an unreadable file
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
            perPath[b] = None  # Not in this file's menu
            continue
        perPath[b] = chain.GetEntries(b)
        terms.append(b)

    if not terms:
        return total, 0, perPath
    # A path missing from the menu is left out of the AND, as the skim's hltHighLevel filter leaves it out
    nPass = chain.GetEntries(("&&" if mode == "all" else "||").join(terms))

    return total, nPass, perPath


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", metavar="NAME", help="Task name under ntupleProduction/jobs/")
    ap.add_argument("--files", nargs="+", metavar="FILE", help="Ntuple files to read; --task is ignored when these are given")
    ap.add_argument("--triggers", metavar="NAME", help="Trigger config, named with its run folder such as run2/lepton; required with --files")
    ap.add_argument("--era", metavar="NAME", help="Era whose paths to read from a trigger config keyed by era; required with --files for such a config, and ignored under --task, which uses each sample's era")
    ap.add_argument("--sample", action="append", metavar="NAME", help="Restrict to these samples")
    ap.add_argument("--perPath", action="store_true", help="Print the per-path breakdown")
    args = ap.parse_args()

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kError

    jobs = []
    if args.files:
        if not args.triggers:
            sys.exit("--files needs --triggers <name>")
        try:
            eras = triggerEras(args.triggers)
            if eras and not args.era:
                sys.exit(f"{args.triggers} keys its paths by era, so --files needs --era with one of: {', '.join(eras)}")
            trig = loadTriggerConfig(args.triggers, era=args.era, triggerDir=paths.TRIGGERS_DIR)
        except (FileNotFoundError, ValueError) as e:
            sys.exit(f"Error: {e}")
        jobs.append(("(files)", args.triggers, trig["paths"], trig["mode"], args.files))
    else:
        if not args.task:
            sys.exit("Give --task or --files")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", args.task):
            sys.exit(f"Bad task name {args.task!r}")
        rec = os.path.join(paths.JOBS_DIR, args.task, "task.json")
        if not os.path.exists(rec):
            sys.exit(f"No task '{args.task}' under {paths.JOBS_DIR}")
        with open(rec) as f:
            info = json.load(f)
        details = {d["name"]: d for d in info.get("sampleDetails", [])}
        wanted = args.sample or info["samples"]
        for name in wanted:
            detail = details.get(name)
            if detail is None:
                print(f"  {name}: not a sample of task '{args.task}', skipping")
                continue
            # The skim the jobs ran with, so editing a preset after the task ran changes nothing here
            skim = taskSkim(info, detail)
            if skim is None:
                print(f"  {name}: task.json holds no resolved content for preset '{detail['content']}', skipping")
                continue
            if not skim.get("hltPaths"):
                print(f"  {name}: content preset '{detail['content']}' declares no trigger skim, skipping")
                continue
            files = findInputs(args.task, name)
            jobs.append((name, skim.get("triggers", "?"), skim["hltPaths"], skim.get("mode", "any"), files))

    hdr = f"{'sample':<42} {'channel':<16} {'files':>5} {'total':>9} {'pass':>9} {'eff':>8}"
    print(hdr)
    print("-" * len(hdr))

    for name, chan, plist, mode, files in jobs:
        if not files:
            print(f"{name:<42} {chan:<16} {'0':>5}   no output files found")
            continue
        total, nPass, perPath = yieldsFor(files, plist, mode)
        eff = 100.0 * nPass / total if total else 0.0
        line = f"{name:<42} {chan:<16} {len(files):>5} {total:>9,} {nPass:>9,} {eff:>7.3f}%"
        print(line)
        if args.perPath:
            for b, n in sorted(perPath.items()):
                mark = "not in menu" if n is None else f"{n:,}"
                print(f"{'':<44} {b:<58} {mark:>12}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
