# Helpers

Small things that are not part of the analysis.

`banner.py`: Draws the Sharingan over the help output. Set `NO_COLOR` to get it without the red.

## Caveats

- `banner.py` writes to stderr, so it stays out of piped output.
- Some LPC sessions are not UTF-8, so the banner is skipped, with no error, when the braille art cannot be printed.
- The banner is drawn only for help output: `main()` checks the arguments before parsing them, and draws it when there are none or one is `-h`/`--help`. Real work never prints it.
