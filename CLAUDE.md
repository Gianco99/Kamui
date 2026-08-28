# Kamui AI Documentation

- Claude Code auto-loads CLAUDE.md files!
- Split by audience: 
  - Per-directory `CLAUDE.md` holds agent context. 
    - Still should be written with humans reading them in mind.
  - `README.md` holds human-facing prose.
    - README.md in the root is the entry point for the repository.
    - Subdirectories carry their own README.md where the detail would bloat the root one.

    - Keep the root pointing at them when necessary.
  - Both are Markdown, so both render on GitHub. 

- Documents for planning or individual studies are stored in `docs/`.
  - These are designed to be transient during the lifetime of their usage. 
  - Finished ones move to `docs/legacy/`, which keeps old studies around so the reasoning behind past decisions stays recoverable
  -  `docs/legacy/README.md` gives the archiving convention.
- Ask the user before making any changes to READMEs or CLAUDE markdowns to ensure changes are intended!


## Writing Docs

- Write prose in normal paragraphs.
- Do not hard-wrap lines at 80 characters or any other column - let the editor naturally wrap.
  - The same applies to code. Do not break a statement across lines to keep it under some column width.
- Tables and bullet lists are fine where the content is genuinely tabular or genuinely a list. Lists are preferred for the ease of human readability.
- Correcting typos is encouraged.
- Blatant errors should be pointed out to the user and not silently corrected.
- Changing a config or a piece of functionality means updating the relevant README.md and CLAUDE.md that reference it.
- When something moves, move its documentation with it.
- Prefer a pointer to a second copy. If a fact belongs somewhere else, name that file instead of restating it.
- Do not put transient facts in a CLAUDE.md at all. 
  - Anything describing the current contents of code goes stale the next time somebody edits that code, and the reader has no way to tell. 
  - State the rule and the reason instead. Measurements belong in docs/, where they are dated results.

- Do not write history. Describe what the code does now, not what it used to do, what it replaced, or why it was changed. 
- Say a thing once, in the fewest words that carry it.
- Never define something by contrast: "it is X, not Y", "X rather than Y", "X is still a Y". State X. The reader was not thinking of Y until it was raised.
- One example, when an example is genuinely needed. Not three.

IMPORTANT: Document why, not just what.


## Conventions

- camelCase everywhere. This is just my (Gianfranco's) preference lol.
- Use `python3`, not `python` - a cmsenv shell leaves `/usr/bin/python` with a mismatched `PYTHONHOME`, so bare `python` fails.
- JSON configs: Keys starting with `_` are comments and are stripped on load.
- In general, we want to stick to the latest, greatest CMSSW releases. However, do not update to new releases without asking the maintainer, Gianfranco. This can introduce errors throughout the repository. So let's stick with the current CMSSW we are working with unless prompted to update.
- Don't use em-dashes when writing docs or coding!


## Coding Principles

- Do not add `__init__.py` files unless something actually needs them.
- Do not break a statement across lines to fit a column width, same as for prose.
- Use American English throughout, in code, comments and documentation: organize, behavior, analyze, center, license.
- Start comments, docstrings, JSON `_doc` strings and anything the user reads, including argparse `help=` text, with a capital letter.
  - Exceptions are things that are naturally lowercase: a variable or function name, a camelCase identifier, a filename, a path, a CMSSW collection, a literal value such as `prod/global`.
- A module docstring opens and closes on its own line, with the text between.
- Group the imports and label the groups with comment headers. A single `#` heading for the whole block, `##` for each group.
- Individual imports get no comment.
- A leading underscore means module-internal. A `_name` is used only inside the file that defines it, and anything imported across modules carries no underscore. `check` does not enforce this, so it is on us to keep true.
