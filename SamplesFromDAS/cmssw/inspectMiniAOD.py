#!/usr/bin/env python3
"""
Report what a MiniAOD file actually contains, so content configs can be written
against facts instead of guesses.

Two things it answers that `edmDumpEventContent` cannot:
  * which b-tag discriminators are embedded in this campaign's jets
  * which electron/muon/tau ID names are embedded in this campaign's leptons
Both move between MiniAOD versions, and a wrong name is either a silent -1000
(b-tags) or a hard exception at runtime (electronID).

Needs cmsenv (uses FWLite). No grid proxy needed for files already on our EOS.

Usage:
  python3 inspectMiniAOD.py root://cmseos.fnal.gov//store/.../file.root [--branches]
"""

import argparse
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="MiniAOD file (local path or xrootd URL)")
    ap.add_argument("--branches", action="store_true", help="also run edmDumpEventContent")
    ap.add_argument("--jets", default="slimmedJetsPuppi")
    args = ap.parse_args()

    if args.branches:
        print("=" * 70)
        print("edmDumpEventContent")
        print("=" * 70)
        r = subprocess.run(["edmDumpEventContent", args.file], capture_output=True, text=True)
        print(r.stdout or r.stderr)

    from DataFormats.FWLite import Events, Handle

    events = Events(args.file)
    handles = {
        "jets":      (Handle("std::vector<pat::Jet>"), args.jets),
        "electrons": (Handle("std::vector<pat::Electron>"), "slimmedElectrons"),
        "muons":     (Handle("std::vector<pat::Muon>"), "slimmedMuons"),
    }

    for ev in events:
        for what, (h, label) in handles.items():
            try:
                ev.getByLabel(label, h)
                coll = h.product()
            except Exception as e:                                  # noqa: BLE001
                print(f"\n--- {what} ({label}): not readable ({e})")
                continue
            if coll.size() == 0:
                print(f"\n--- {what} ({label}): empty in this event, try another")
                continue
            obj = coll[0]
            print(f"\n--- {what} ({label}), {coll.size()} in event 1")
            if what == "jets":
                names = [str(p.first) for p in obj.getPairDiscri()]
                print(f"  {len(names)} b-tag discriminators:")
                for n in sorted(names):
                    print(f"    {n}")
            else:
                ids = [str(p.first) for p in obj.electronIDs()] if what == "electrons" else []
                if ids:
                    print(f"  {len(ids)} embedded IDs:")
                    for n in sorted(ids):
                        print(f"    {n}")
            uf = [str(x) for x in obj.userFloatNames()]
            ui = [str(x) for x in obj.userIntNames()]
            if uf:
                print(f"  userFloats: {', '.join(sorted(uf))}")
            if ui:
                print(f"  userInts  : {', '.join(sorted(ui))}")
        break                                                        # one event is enough
    return 0


if __name__ == "__main__":
    sys.exit(main())
