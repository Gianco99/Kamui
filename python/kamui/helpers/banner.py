"""
The startup banner. Decoration only.
"""

# Import Block

## Standard Python imports
import os
import sys

SHARINGAN = """\
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣠⣤⣤⣤⣤⣄⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⣠⣶⣿⣿⣿⣿⡿⠃⠘⢿⣿⣿⣿⣿⣶⣄⡀⠀⠀⠀⠀⠀
⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣿⡿⠁⠀⠀⠈⢿⣿⣿⣿⣿⣿⣿⣦⡀⠀⠀⠀
⠀⠀⣰⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿⣆⠀⠀
⠀⣸⣿⡉⠀⡀⠈⠉⠉⢙⡟⠲⠤⣄⣠⠤⠖⢻⡋⠉⠉⠁⠀⠀⠉⣿⣧⠀
⢰⣿⣿⣷⡀⠈⢻⣷⣶⣼⣤⣔⠊⠁⠈⠑⣢⣤⣧⣶⣾⡿⠁⢀⣾⣿⣿⡆
⣼⣿⣿⣿⣿⣄⠀⢉⡿⣿⣿⣿⡿⠖⠲⢿⣿⣿⣿⠿⡋⠀⣠⣾⣿⣿⣿⣷
⣿⣿⣿⣿⣿⣿⡷⣏⠀⡏⠻⢿⡁⠀⠀⢈⡿⠟⢹⠀⣨⢾⣿⣿⣿⣿⣿⣿
⢻⣿⣿⣿⡿⠋⠀⠈⠳⣧⡀⠀⣷⣦⣴⣾⠀⢀⣸⠞⠁⠀⠙⢿⣿⣿⣿⡿
⠸⣿⣿⡿⠁⠀⠀⠀⠀⢸⠉⠲⢼⣿⣿⡯⠖⠋⡇⠀⠀⠀⠀⠈⢿⣿⣿⠇
⠀⠹⣿⣀⣀⣀⣀⣀⣀⣨⣧⠔⠚⣿⣿⠗⠢⢼⣅⣀⣀⣀⣀⣀⣀⣿⡏⠀
⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⢻⡿⠀⢠⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀
⠀⠀⠀⠈⠻⣿⣿⣿⣿⣿⣿⣷⡀⠈⠃⢀⣾⣿⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀
⠀⠀⠀⠀⠀⠈⠙⠻⢿⣿⣿⣿⣷⣄⢠⣾⣿⣿⣿⡿⠿⠋⠁⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠙⠛⠛⠛⠛⠋⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀"""

RED, RESET = "\033[31m", "\033[0m"


def printBanner(enabled=True, stream=None):
    """Draw the Sharingan. Does nothing whenever it would be unwelcome."""
    stream = stream or sys.stderr
    if not enabled:
        return
    if not hasattr(stream, "isatty") or not stream.isatty():
        return                              # piped or redirected: keep the output clean
    art = SHARINGAN
    if not os.environ.get("NO_COLOR"):
        art = "\n".join(RED + line + RESET for line in art.split("\n"))
    try:
        stream.write(art + "\n")
    except UnicodeEncodeError:
        pass                                # terminal cannot do braille; no banner, no crash
