#!/usr/bin/env python3
"""Report the b-tag discriminators, embedded IDs and user data a MiniAOD file carries. Needs cmsenv."""

import argparse
import subprocess
import sys

MAX_EVENTS = 100


def _report(what, label, obj, size):
    print(f"\n--- {what} ({label}), {size} in this event")
    if what == "jets":
        names = sorted(str(p.first) for p in obj.getPairDiscri())
        print(f"  {len(names)} b-tag discriminators:")
        for n in names:
            print(f"    {n}")
    elif what == "electrons":
        ids = sorted(str(p.first) for p in obj.electronIDs())
        if ids:
            print(f"  {len(ids)} embedded IDs:")
            for n in ids:
                print(f"    {n}")
    uf = sorted(str(x) for x in obj.userFloatNames())
    ui = sorted(str(x) for x in obj.userIntNames())
    if uf:
        print(f"  userFloats: {', '.join(uf)}")
    if ui:
        print(f"  userInts  : {', '.join(ui)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="MiniAOD file (local path or xrootd URL)")
    ap.add_argument("--branches", action="store_true", help="Also run edmDumpEventContent")
    ap.add_argument("--jets", default="slimmedJetsPuppi", help="Jet collection to read (default: slimmedJetsPuppi)")
    args = ap.parse_args()

    if args.branches:
        print("=" * 70)
        print("edmDumpEventContent")
        print("=" * 70)
        r = subprocess.run(["edmDumpEventContent", args.file], capture_output=True, text=True)
        print(r.stdout or r.stderr)

    from DataFormats.FWLite import Events, Handle

    handles = {
        "jets": (Handle("std::vector<pat::Jet>"), args.jets),
        "electrons": (Handle("std::vector<pat::Electron>"), "slimmedElectrons"),
        "muons": (Handle("std::vector<pat::Muon>"), "slimmedMuons"),
    }
    ## A collection can be empty in any given event, so each one is reported from the first
    ## event that actually has it rather than from event 1.
    pending = dict(handles)
    for n, ev in enumerate(Events(args.file)):
        if not pending or n >= MAX_EVENTS:
            break
        for what, (h, label) in list(pending.items()):
            try:
                ev.getByLabel(label, h)
                coll = h.product()
            except Exception as e:
                print(f"\n--- {what} ({label}): not readable ({e})")
                del pending[what]
                continue
            if coll.size():
                _report(what, label, coll[0], coll.size())
                del pending[what]

    for what, (_, label) in pending.items():
        print(f"\n--- {what} ({label}): empty in the first {MAX_EVENTS} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
