# Kamui AI Documentation

- Kept as `.md` because Claude Code auto-loads CLAUDE.md.
- Split by audience: Per-directory `CLAUDE.md` holds agent context, and human-facing prose is plain `.txt`. CLAUDE.md files should still be written with humans reading it in mind.
- README.txt in the root is the entry point for the repository. Subdirectories carry their own README.txt where the detail would bloat the root one. Keep the root pointing at them rather than repeating them.
- Documents for planning or individual studies are stored in `docs/`. These are designed to be transient during the lifetime of their usage. Finished ones move to `docs/legacy/`, which keeps old studies around so the reasoning behind past decisions stays recoverable; `docs/legacy/README.txt` gives the archiving convention.
- Ask the user before making any changes to READMEs or CLAUDE markdowns to ensure changes are intended!


## Writing Docs

- Write prose in normal paragraphs.
- Do not hard-wrap lines at 80 characters or any other column - let the editor naturally wrap. A paragraph is one long line. Hard-wrapped text is miserable to edit and produces garbage diffs when a single word changes.
- The same applies to code. Do not break a statement across lines to keep it under some column width. One statement is one line, however long it ends up.
- Tables and bullet lists are fine where the content is genuinely tabular or genuinely a list. Lists are preferred for the ease of human readability.
- Correcting typos is encouraged.
- Blatant errors should be pointed out to the user and not silently correct.

IMPORTANT: Document why, not just what. Date anything that could go stale. Keep it short and not extremely verbose unless deemed necessary.


## Conventions

- camelCase everywhere: variables, functions, filenames, JSON keys. This is just Gianfranco's preference lol.
- Use `python3`, not `python` - a cmsenv shell leaves `/usr/bin/python` with a mismatched `PYTHONHOME`, so bare `python` fails.
- JSON configs: Keys starting with `_` are comments and are stripped on load.
- In general, we want to stick to the latest, greatest CMSSW releases. However, do not update to new releases without asking the maintainer, Gianfranco. This can introduce errors throughout the repository. So let's stick with the current CMSSW we are working with unless prompted to update.


## Coding Principles

- Do not add `__init__.py` files unless something actually needs them.
- Do not break a statement across lines to fit a column width, same as for prose.
- Use American English throughout, in code, comments and documentation: organize, behavior, analyze, center, license.
- A module docstring opens and closes on its own line, with the text between:
- Group the imports and label the groups with comment headers. A single `#` heading for the whole block, `##` for each group.
- Individual imports get no comment.


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

The release version and arch are also recorded in `SamplesFromDAS/config/sites.json`, which is what condor jobs read; keep the two consistent.
Nothing in the repo should hardcode a username - `sites.json` uses `$USER`, expanded when the config is loaded on the submitting machine.


## Repository Structure

- Root holds the README.txt, this file, `.gitignore` and `kamui`, the CLI entry point.
- Everything else lives in a subdirectory, and each carries its own CLAUDE.md containing details for the workings of that particular subdirectory:
- `python/kamui/` — The framework itself, shared by every analysis stage → `python/kamui/CLAUDE.md` for design notes, `python/kamui/README.txt` for the CLI reference
- `SamplesFromDAS/` — Sample processing: the DAS catalog, configuration files, triggers used and job submission → `SamplesFromDAS/CLAUDE.md`
- `docs/` — Transient documentation for current studies; finished ones move to `docs/legacy/` → `docs/legacy/README.txt` for the archiving convention
