"""Backward-compatible module for historical imports.

The production implementation now lives under aks_ip_diagnostic/.  This module
remains intentionally tiny so old commands such as `python src/main.py ...` and
old tests importing `main.run_diagnostic` keep working during migration.
"""

from __future__ import annotations

import sys

from aks_ip_diagnostic.cli import build_parser
from aks_ip_diagnostic.scan_runner import run_diagnostic


def parse_arguments():
    """Parse legacy scan arguments.

    The modern CLI supports subcommands.  For direct `python src/main.py` usage,
    we parse the same arguments as `aks-ip-diagnostic scan`.
    """

    parser = build_parser()
    return parser.parse_args(["scan", *sys.argv[1:]])


def main() -> int:
    """Run the scanner through the modern CLI implementation."""

    args = parse_arguments()
    return run_diagnostic(args)


if __name__ == "__main__":
    sys.exit(main())
