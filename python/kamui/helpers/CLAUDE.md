# helpers/

- `banner.py` writes to stderr, so it stays out of piped output.
- Non-UTF-8 environments turn up on LPC, so the braille art is wrapped for `UnicodeEncodeError` rather than assuming a terminal can encode it.
- The banner is drawn only for help output: `main()` scans raw `argv` before `parse_args` and draws when the arguments are empty or carry `-h`/`--help`. Real work never prints it.
