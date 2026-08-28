# config/selections

`README.md` covers the schema and how to run a selection. This is what to be careful about.

## The Two Run 2 Configs Are Frozen Against JMTucker

`run2Lepton.json` and `run2Displaced.json` are validated against JMTucker event for event, in both channels across all four Run 2 eras. Every number in them is load-bearing: a threshold, a b-tag working point, a pT ladder, an ID requirement, a path list. Changing one breaks the agreement, and the agreement is the reason these files exist. A new study gets a new file.

## The Lepton Veto Is The Lepton Selection, Inverted

The `leptonVeto` cut in `run2Displaced.json` has legs byte-identical to the `leptonPlateau` legs in `run2Lepton.json`, with `invert: true` on the cut. That is deliberate and worth preserving. A hand-written negation would have to invert an OR of three trigger-gated legs each carrying six requirements with per-era thresholds, and the two channels stay provably disjoint only while the two statements are the same statement. If a threshold moves in `run2Lepton.json` it has to move in `leptonVeto` in the same edit, and the invariant to check is that the two `anyOf` lists compare equal as JSON.

Two things about that cut come from JMTucker and look like omissions. `Mu50`, `Ele115` and `Ele50_PFJet165` are in the `run2Lepton` trigger config but not in the veto's leg gating, because JMTucker's veto skips them. And `run2Lepton.json` carries no orthogonality veto of its own, because in JMTucker the veto belongs to the displacement channel.

## anyOf Is Two Different Keys

Inside an `object` cut, `anyOf` is a list of legs: each entry has `collection`, `requirements` and the rest of the leg fields, and the OR is over which collection supplied a passing object. As a cut `type`, `anyOf` is a list of alternatives: each entry has `cuts`, an ordinary cut list ANDed together, and the OR is over which whole group passed. The two are validated against different rules, `LEG_FIELDS` for a leg and nothing more than a check for `cuts` on an alternative, and which one applies is decided entirely by the enclosing cut's `type`.

Both forms are needed. The leg form expresses "a muon or an electron", where the alternatives share the surrounding cut. The cut-type form expresses "any of eleven displacement triggers, each with its own offline emulation", where each alternative is several cuts of different types.

## A Trigger Pattern That Matches No Branch Rejects Everything

`triggerMask` returns an all-false mask when no branch matched any pattern, so a misspelled path, or a path absent from the ntuple's stored branches, silently kills the cut and the whole channel with it. The cutflow note is the only warning: it reads `0/1 paths present`, and the count of matched paths is the thing to read when a selection returns zero events.

Flags fail in the opposite direction. A flag missing from the file is skipped and its events still pass, so a misspelled flag makes the cut looser than written. The note appends `MISSING [...]` in that case.

## `eras` Only Does Something On An `anyOf` Alternative

`CUT_FIELDS` lists `eras`, so the validator accepts it on any cut, but the only code that reads it is the alternative loop in `_resolveCut`. A cut carrying `eras` at the top level passes validation and then applies in every era. To era-gate something, either wrap it in an `anyOf` alternative or key its thresholds by era.

## `./kamui check` Does Not Look At These Files

`check` validates the catalog, the content presets and the trigger configs. `resolveSelection` is called from one place, `_cmdSelect`, so a broken selection config is only discovered when someone runs `select` with it. After editing here, run a real `select` against a small sample.

## A `veto` Is Already Negated

A `veto` computes `~(fired & conditions)`. Adding `invert` to one hands back exactly the events it exists to remove. A veto also cannot be written without an offline condition: with no `conditions` and no inline `quantity`, the reader reports an unknown quantity `None`. A pure trigger veto is a `trigger` cut with `invert`.

## The `anyOf` Note Counts All Input Events

Each cut's mask is computed over the full array, and the running mask is applied afterwards in `applySelection`. So the `kept`, `removed` and `efficiency` columns of the cutflow are properly sequential, while the per-alternative counts inside an `anyOf` cut's detail string are over every input event with no upstream cut applied. They do not sum to the cut's own `kept`, and they are not meant to.

Sub-cuts inside an alternative never appear in the cutflow, and `--cutflow` writes one ntuple per top-level cut only.

## An Object Cut Selects Events

Nothing is removed from the collections. `applySelection` writes an ntuple with the same branches as the input, which is what makes a selection pass composable with the next one. `_write` regroups each collection into one record so uproot emits one counter per collection: written branch by branch, a file that went in with `nElectron` would come out with `nElectron_pt`, `nElectron_eta` and so on.

## Small Traps In The Reader

A leg's `min` goes through a plain `int(...)`, so writing it as an era-keyed object raises a `TypeError` from inside the reader. Every real threshold becomes a `float`, so an integer-valued ID is written `"min": 1` and compared as `>= 1.0`; `"min": true` is rejected. `orderedMinPt` must be descending, and the reader refuses a ladder that is not, because it is matched against pT-sorted objects.

Selection configs go through `loadWithIncludes`, so `include` works here, but `deepMerge` replaces lists wholesale. Including another selection and adding one cut is not possible: the child's `cuts` list wins entirely.
