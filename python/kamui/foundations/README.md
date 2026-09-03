# foundations/

The bottom layer everything else is built on.

`paths.py` - Knows the paths where everything lives. It works this out from its own location, so there is nothing to set up and the framework runs wherever you check it out.

`config.py` - Reads the JSON config files.
- Any key starting with an underscore is treated as a comment and dropped, since JSON has no comment syntax.
- Config files inherit from each other like C++ classes, through an `include` list naming what to build on.
  - Overriding a block replaces only the parts you name, so the settings originally defined survive.
  - Lists are the exception. There is no way to say "the base list plus mine", so restate anything you want to keep.
