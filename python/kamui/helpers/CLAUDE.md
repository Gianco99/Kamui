# helpers/

- `banner.py` writes to stderr, not stdout, so it can never contaminate piped output.
- It draws only when stderr is a terminal, keeping scripts, cron and log files clean.
- The braille art is wrapped in a `try` for `UnicodeEncodeError`, so a terminal that cannot encode it gets no banner. This matters on LPC, where non-UTF-8 environments turn up.
- The banner is drawn only for help output: `main()` scans raw `argv` before `parse_args` and draws when the arguments are empty or carry `-h`/`--help`. Real work never prints it. `--noBanner` is registered so `--help` documents it and is read from raw argv, so `args.noBanner` is never used. It sits on the top-level parser and has to precede the command.
