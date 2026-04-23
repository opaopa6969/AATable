"""Tests for aatable.parse_md_table()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aatable


def test_basic_table():
    lines = ["| a | b |", "|---|---|", "| 1 | 2 |"]
    result = aatable.parse_md_table(lines)
    assert result is not None
    assert ["a", "b"] in result
    assert ["1", "2"] in result


def test_empty_input():
    result = aatable.parse_md_table([])
    assert result is None or result == []


def test_separator_only():
    result = aatable.parse_md_table(["|---|---|"])
    assert result is None or result == []


def test_colon_alignment():
    lines = ["| h |", "|:---:|", "| v |"]
    result = aatable.parse_md_table(lines)
    assert result is not None
    # Should have "h" and "v" rows (separator stripped)
    values = [row[0] for row in result]
    assert "h" in values
    assert "v" in values
