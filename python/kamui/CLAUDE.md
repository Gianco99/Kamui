# Kamui

## Design Premise
- Kamui is the CLI for the whole analysis framework.
- Two stages exist: sample processing (`submit`) and event selection (`select`).
- When a new stage is added it belongs here as commands.

The design principle the whole package serves is that the physics lives in configuration files and this code only executes what they say.
## Main Driver - cli.py
- Every command lives in this one file. 
  - Adding one is two edits here: a `_cmdX` handler, and an `_addCmd(sub, ...)` block that points at it. 
  - Registration order is the order `--help` lists them, and it follows the root README's command table.
- Keep it thin. It parses, calls a module, and prints. The actual behavior belongs in the modules so they can be imported without the CLI.

## Where The Rest Is

Each subfolder carries its own `CLAUDE.md`: `foundations/`, `configReaders/`, `grid/`, `submit/`, `select/` and `helpers/`.
