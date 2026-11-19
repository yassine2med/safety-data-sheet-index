"""Command line entry point."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .core import build_index, find_problems, scan_folder


def main(argv: list[str] | None = None) -> int:
    """Print the index and any problems. Exit code 1 if problems exist."""
    parser = argparse.ArgumentParser(prog="sds_index")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--max-age-years", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        sheets = scan_folder(args.folder)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(build_index(sheets))
    problems = find_problems(sheets, args.as_of, args.max_age_years)
    if problems:
        print("\nProblems:")
        for p in problems:
            print(f"- {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
