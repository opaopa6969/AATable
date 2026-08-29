"""Tests for aatable.parse_auto()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aatable


def test_csv_with_pipe_cell_not_misdetected_as_markdown():
    # Issue #31: a CSV whose cell value starts with '|' must not be parsed as
    # Markdown, otherwise rows not starting with '|' are silently dropped.
    lines = ["a,b\n", "|,2\n", "3,4\n"]
    result = aatable.parse_auto(lines)
    assert result == [["a", "b"], ["|", "2"], ["3", "4"]]


def test_markdown_table_still_detected():
    # A real Markdown table (all non-empty lines start with '|') is detected.
    lines = ["| a | b |\n", "|---|---|\n", "| 1 | 2 |\n"]
    result = aatable.parse_auto(lines)
    assert result == [["a", "b"], ["1", "2"]]


def test_tsv_detected_when_not_markdown():
    lines = ["a\tb\n", "1\t2\n"]
    result = aatable.parse_auto(lines)
    assert result == [["a", "b"], ["1", "2"]]


def test_csv_detected_by_default():
    lines = ["a,b\n", "1,2\n"]
    result = aatable.parse_auto(lines)
    assert result == [["a", "b"], ["1", "2"]]
