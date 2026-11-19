from datetime import date
from pathlib import Path

import pytest

from sds_index.__main__ import main
from sds_index.core import build_index, find_problems, parse_sheet, scan_folder

TODAY = date(2026, 11, 19)
GOOD = "Product name: Foo\nManufacturer: Acme\nCAS Number: 64-17-5\nRevision date: 2025-01-01\n"


def test_parse_fields():
    s = parse_sheet(GOOD, "foo.txt")
    assert (s.product, s.manufacturer, s.cas) == ("Foo", "Acme", "64-17-5")
    assert s.revision == date(2025, 1, 1)


def test_parse_case_insensitive_keys():
    assert parse_sheet("PRODUCT NAME: Bar").product == "Bar"


def test_parse_empty_text():
    s = parse_sheet("")
    assert s.product == "" and s.revision is None


def test_parse_bad_revision_is_none():
    assert parse_sheet("Revision date: soon").revision is None


def test_first_value_wins():
    assert parse_sheet("Product name: A\nProduct name: B").product == "A"


def test_no_problems_for_good_sheet():
    assert find_problems([parse_sheet(GOOD, "foo.txt")], TODAY) == []


def test_stale_sheet_flagged():
    old = parse_sheet(GOOD.replace("2025-01-01", "2020-01-01"), "old.txt")
    assert any("older than 3 years" in p for p in find_problems([old], TODAY))


def test_age_limit_configurable():
    s = parse_sheet(GOOD, "foo.txt")
    assert find_problems([s], TODAY, max_age_years=1)


def test_bad_cas_flagged():
    s = parse_sheet(GOOD.replace("64-17-5", "6417"), "x.txt")
    assert any("bad format" in p for p in find_problems([s], TODAY))


def test_duplicates_flagged_case_insensitive():
    a, b = parse_sheet(GOOD, "a.txt"), parse_sheet(GOOD.replace("Foo", "FOO"), "b.txt")
    assert any("duplicate product" in p for p in find_problems([a, b], TODAY))


def test_index_sorted_and_marks_unknown():
    a = parse_sheet("Product name: Zed", "z.txt")
    b = parse_sheet("Product name: Alpha", "a.txt")
    lines = build_index([a, b]).splitlines()
    assert "Alpha" in lines[2] and "unknown" in lines[3]


def test_scan_example_folder():
    assert len(scan_folder(Path("examples/sds"))) == 5


def test_scan_missing_folder():
    with pytest.raises(ValueError):
        scan_folder(Path("does-not-exist"))


def test_cli_exit_codes():
    assert main(["examples/sds", "--as-of", "2026-11-19"]) == 1
    assert main(["nope"]) == 2
