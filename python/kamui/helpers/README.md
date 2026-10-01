# Helpers

Small things that are not part of the analysis.

`banner.py`: Draws the Sharingan over the help output. Set `NO_COLOR` to get it without the red.

## Caveats

- `banner.py` writes to stderr, so it stays out of piped output.
- Non-UTF-8 environments turn up on LPC, so the braille art is drawn inside a `UnicodeEncodeError` guard.
- The banner is drawn only for help output: `main()` scans raw `argv` before `parse_args` and draws when the arguments are empty or carry `-h`/`--help`. Real work never prints it.
