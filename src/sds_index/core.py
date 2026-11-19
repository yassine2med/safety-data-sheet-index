"""Index safety data sheet (SDS) text files by product and flag stale revisions."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FIELDS = {
    "product name": "product",
    "manufacturer": "manufacturer",
    "cas number": "cas",
    "revision date": "revision",
}
CAS_PATTERN = re.compile(r"^\d{2,7}-\d{2}-\d$")


@dataclass(frozen=True)
class Sheet:
    """Fields read from one SDS text file."""

    path: str
    product: str
    manufacturer: str
    cas: str
    revision: date | None


def parse_sheet(text: str, path: str = "") -> Sheet:
    """Read 'Field: value' lines from SDS text. Missing fields stay empty."""
    found: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        name = FIELDS.get(key.strip().lower())
        if sep and name and name not in found:
            found[name] = value.strip()
    revision = None
    if found.get("revision"):
        try:
            revision = date.fromisoformat(found["revision"])
        except ValueError:
            revision = None
    return Sheet(path, found.get("product", ""), found.get("manufacturer", ""),
                 found.get("cas", ""), revision)


def scan_folder(folder: Path) -> list[Sheet]:
    """Parse every .txt file below folder."""
    if not folder.is_dir():
        raise ValueError(f"not a folder: {folder}")
    return [parse_sheet(p.read_text(encoding="utf-8"), p.name)
            for p in sorted(folder.rglob("*.txt"))]


def find_problems(sheets: list[Sheet], today: date, max_age_years: int = 3) -> list[str]:
    """List missing fields, bad CAS numbers, stale sheets and duplicate products."""
    problems: list[str] = []
    by_product: dict[str, list[str]] = defaultdict(list)
    for s in sheets:
        if not s.product:
            problems.append(f"{s.path}: no product name")
            continue
        by_product[s.product.lower()].append(s.path)
        if s.revision is None:
            problems.append(f"{s.path}: missing or invalid revision date")
        elif (today - s.revision).days > max_age_years * 365:
            problems.append(f"{s.path}: revision {s.revision} is older than {max_age_years} years")
        if s.cas and not CAS_PATTERN.match(s.cas):
            problems.append(f"{s.path}: CAS number '{s.cas}' has a bad format")
    for product, paths in by_product.items():
        if len(paths) > 1:
            problems.append(f"duplicate product '{product}': {', '.join(paths)}")
    return problems


def build_index(sheets: list[Sheet]) -> str:
    """Return a Markdown table sorted by product name."""
    rows = ["| Product | Manufacturer | CAS | Revision | File |", "|---|---|---|---|---|"]
    for s in sorted(sheets, key=lambda x: x.product.lower()):
        rev = s.revision.isoformat() if s.revision else "unknown"
        rows.append(f"| {s.product or 'unknown'} | {s.manufacturer or 'unknown'} | "
                    f"{s.cas or 'unknown'} | {rev} | {s.path} |")
    return "\n".join(rows)
