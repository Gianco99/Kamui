# Helpers

This folder holds the CLI's cosmetic extras.

`banner.py`: Draws the Sharingan banner above the help output. Set `NO_COLOR` to get it without the red.

## Caveats

- `banner.py` writes to stderr, so the banner stays out of piped output.
- Some LPC sessions are not UTF-8. When the braille art can't be printed, the banner is skipped with no error.
- The banner is drawn only for help output. `main()` checks the arguments before parsing them, and draws it when there are none or one of them is `-h` or `--help`, so real work never prints it.
