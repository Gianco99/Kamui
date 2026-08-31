# config/content
## Caveats

- A preset is resolved, not read. Run `./kamui content <name> --era <era>`; the file alone tells you almost nothing.
- `--data` changes the answer, so every preset must work both ways. `check` resolves each one both ways.
- An `include` name resolves against the era set, then subdirectories in sorted order, so `collections/` beats `presets/`. They cannot share a name.
- Overrides deep-merge, so one key can be replaced without restating the rest. Lists replace wholesale.
- `expr` is C++ evaluated at job runtime. `check` cannot catch a typo; it survives until a job dies on the grid. `cmssw/inspectMiniAOD.py` lists what a file carries.
  - `bDiscriminator()` returns -1000 for a missing tagger, `electronID()` throws.
- `precision: -1` for anything a selection threshold compares against. Truncation quantizes pT enough to push an object onto a threshold.
  - Includes `vx`, `vy`, `vz` and the `PV` positions, which the selection recomputes impact parameters from.
- `GenPart` takes no `cut` and `PV` no `maxLen`. `genPartIdxMother` and `Track_pvIdx` index them positionally, so either silently repoints every link. Capping `PV` also breaks pileup counting.
- `maxLen` truncates in source order with no sort. Jets arrive pT-ordered, `SV` does not.
- `core` supplies `run`, `luminosityBlock` and `event` without being asked. Its `triggerBits` needs all of `HLT`, `PAT` and `RECO` because MET filter decisions live in PAT for MC and RECO for data.
- Editing a collection changes every preset that includes it, in both era sets. Anything already produced stops being comparable.

## The Era Split Is A Wall

`contentDirs` returns one directory, so a Run 2 sample can never resolve a Run 3 config. A wrong-era accessor fails at job runtime: `electronID('mvaEleID-RunIIIWinter22-iso-V1-wp90')` throws on a Run 2 file.

`validateEraCopies` byte-compares the two copies. All must be identical except `ERA_SPECIFIC_COLLECTIONS`, which must differ:

- `leptons`, in the electron ID names, Fall17-94X-V2 against RunIIIWinter22-V1.
- `jets`, in `Jet.src`, CHS `slimmedJets` for Run 2 to match JMTucker, `slimmedJetsPuppi` for Run 3.
