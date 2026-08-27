"""
Worker-side entry point: apply one resolved selection to one group of input files.

Run as `python3 -m kamui.select.runOne <selectionJson> <outputFile> <input> [input ...]`.
The selection arrives already resolved, so the worker never reads a config directory.
"""

# Import Block

## Standard Python imports
import json
import sys

## Kamui modules
from .engine import applySelection


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 3:
        sys.exit("usage: runOne.py <selectionJson> <outputFile> <input> [input ...]")

    selectionPath, outputPath, inputs = argv[0], argv[1], argv[2:]
    with open(selectionPath) as f:
        selection = json.load(f)

    flow = applySelection(inputs, selection, outputPath)

    ## The cutflow travels back with the output so the driver can merge it
    with open(outputPath + ".cutflow.json", "w") as f:
        json.dump(flow, f, indent=2)

    for row in flow:
        print(f"[select] {row['cut']:<16} {row['kept']:>10,}  {100 * row['efficiency']:>6.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
