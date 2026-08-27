# Kamui AI Documentation

- Kept as `.md` because Claude Code auto-loads CLAUDE.md.
- Split by audience: Per-directory `CLAUDE.md` holds agent context, and human-facing prose is plain `.txt`. CLAUDE.md files should still be written with humans reading it in mind.
- README.txt in the root is the entry point for the repository. Subdirectories carry their own README.txt where the detail would bloat the root one. Keep the root pointing at them.
- Documents for planning or individual studies are stored in `docs/`. These are designed to be transient during the lifetime of their usage. Finished ones move to `docs/legacy/`, which keeps old studies around so the reasoning behind past decisions stays recoverable; `docs/legacy/README.txt` gives the archiving convention.
- Ask the user before making any changes to READMEs or CLAUDE markdowns to ensure changes are intended!


## Writing Docs

- Write prose in normal paragraphs.
- Do not hard-wrap lines at 80 characters or any other column - let the editor naturally wrap. A paragraph is one long line. Hard-wrapped text is miserable to edit and produces garbage diffs when a single word changes.
- The same applies to code. Do not break a statement across lines to keep it under some column width. One statement is one line, however long it ends up.
- Tables and bullet lists are fine where the content is genuinely tabular or genuinely a list. Lists are preferred for the ease of human readability.
- Correcting typos is encouraged.
- Blatant errors should be pointed out to the user and not silently corrected.
- Changing a config or a piece of functionality means updating the CLAUDE.md that covers it, in the same edit.
- When something moves, move its documentation with it. Do not leave a copy behind. Ex: if offline selections are currently recorded as pending in the trigger CLAUDE.md and later get applied in code, the note goes away and the explanation lives where the cut is made.
- Prefer a pointer to a second copy. If a fact belongs somewhere else, name that file instead of restating it.
- Do not put transient facts in a CLAUDE.md at all. Anything describing the current contents of code, a list of entries, a count, a measurement from one sample, goes stale the next time somebody edits that code, and the reader has no way to tell. State the rule and the reason instead: "keeps are label-first because a wrong class name silently keeps nothing" survives any edit, "the jets group drops tagInfos" does not. Measurements belong in docs/, where they are dated results.
- The test before writing a line: would this still be true after someone edits the file it describes? If not, it belongs in the code as a comment, or nowhere.
- Do not write history. Describe what the code does now, not what it used to do, what it replaced, or why it was changed. A reader wants the current state; git holds the rest. Phrases like "this used to", "kept deliberately", "was removed on", "the old workflow" are the tell.
- Say a thing once, in the fewest words that carry it. A second sentence restating the first, a list of examples where one would do, or an aside contrasting the point with what it is not, all bury the sentence that matters. Cut them.
- Never define something by contrast: "it is X, not Y", "X rather than Y", "X is still a Y". State X. The reader was not thinking of Y until it was raised.
- One example, when an example is genuinely needed. Not three.

IMPORTANT: Document why, not just what. A date is for recording when something was established, not a license to write something that will rot. Keep it short and not extremely verbose unless deemed necessary.


## Conventions

- camelCase everywhere: variables, functions, filenames, JSON keys. This is just Gianfranco's preference lol.
- Use `python3`, not `python` - a cmsenv shell leaves `/usr/bin/python` with a mismatched `PYTHONHOME`, so bare `python` fails.
- JSON configs: Keys starting with `_` are comments and are stripped on load.
- In general, we want to stick to the latest, greatest CMSSW releases. However, do not update to new releases without asking the maintainer, Gianfranco. This can introduce errors throughout the repository. So let's stick with the current CMSSW we are working with unless prompted to update.


## Coding Principles

- Do not add `__init__.py` files unless something actually needs them.
- Do not break a statement across lines to fit a column width, same as for prose.
- Use American English throughout, in code, comments and documentation: organize, behavior, analyze, center, license.
- Start comments, docstrings, JSON `_doc` strings and anything the user reads, including argparse `help=` text, with a capital letter. Exceptions are things that are naturally lowercase: a variable or function name, a camelCase identifier, a filename, a path, a CMSSW collection, a literal value such as `prod/global`.
- A module docstring opens and closes on its own line, with the text between.
- Group the imports and label the groups with comment headers. A single `#` heading for the whole block, `##` for each group.
- Individual imports get no comment.
- A leading underscore means module-internal. A `_name` is used only inside the file that defines it, and anything imported across modules carries no underscore. `check` does not enforce this, so it is on us to keep true.


## Environment

Needs CMSSW_16_1_2, the pinned version. Create the release area once, anywhere you like. The CMSSW release itself should not be committed to the repository, only the code and instructions for first time set-up. Individual users should set-up and compile CMSSW themselves on their local LPC instances. Below are example commands to set-up CMSSW_16_1_2:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el9_amd64_gcc13
cmsrel CMSSW_16_1_2
```

Then per session, from that release's `src/`:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el9_amd64_gcc13
cmsenv
voms-proxy-init --rfc --voms cms -valid 192:00
```

The release version and arch are also recorded in `config/sites.json`, which is what condor jobs read; keep the two consistent.
Nothing in the repo should hardcode a username - `sites.json` uses `$USER`, expanded when the config is loaded on the submitting machine.


## Repository Structure

- Root holds the README.txt, this file, `.gitignore` and `kamui`, the CLI entry point.
- Everything else lives in a subdirectory. Subdirectories carry their own CLAUDE.md where there is agent-facing context to record:
- `python/kamui/` — The framework itself, shared by every analysis stage → `python/kamui/CLAUDE.md` for design notes, `python/kamui/README.txt` for the CLI reference
- `config/` — Sample, content, trigger and site configs, read by every stage → `config/CLAUDE.md`
- `ntupleProduction/` — Turning datasets into ntuples: the cmsRun config, the tables it builds, and the generated job areas → `production/CLAUDE.md`
- `tools/` — Standalone scripts for checking output, run by hand
- `docs/` — Transient documentation for current studies; finished ones move to `docs/legacy/` → `docs/legacy/README.txt` for the archiving convention
