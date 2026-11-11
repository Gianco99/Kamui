# tools/triggerYields.py decides which trigger paths exist from the first file of a sample only.

- **Where:** `tools/triggerYields.py`, `yieldsFor` (the `have` set built from `chain.GetListOfBranches()`).
- **Problem:** `TChain.GetListOfBranches()` lists the first file's branches, so a path missing from that file but present in later ones is counted as absent for the whole sample. With `mode: "all"` it is left out of the AND, and with `--perPath` it shows as `not in menu`. This only matters when a sample's files come from different HLT menus, as in data.
- **Fix:** Build `have` from the union of the branches of every file, and count a path as not fired in the files that lack it, as `select` does.
