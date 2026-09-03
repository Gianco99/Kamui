# Kamui

## Design Premise
- Kamui is the CLI for the whole analysis framework.
- Two stages exist: sample processing (`submit`) and event selection (`select`).
- When a new stage is added it belongs here as commands.

The design principle the whole package serves is that the physics lives in configuration files and this code only executes what they say.

## Main Driver - cli.py
- Keep it thin. It parses, calls a module, and prints. The actual behavior belongs in the modules so they can be imported without the CLI.
- Command registration order is the order `--help` lists them, and it follows the README's command order.
