"""Tests for aatable.parse_csv()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aatable


def test_parse_csv_without_newlines():
    # Issue #32: elements without trailing newlines must not be merged.
    assert aatable.parse_csv(['a,b', '1,2']) == [['a', 'b'], ['1', '2']]


def test_parse_csv_with_newlines():
    assert aatable.parse_csv(['a,b\n', '1,2\n']) == [['a', 'b'], ['1', '2']]


def test_parse_csv_newline_invariant():
    # With and without newlines must produce identical results.
    assert aatable.parse_csv(['a,b', '1,2']) == aatable.parse_csv(['a,b\n', '1,2\n'])


def test_parse_csv_skips_blank_rows():
    assert aatable.parse_csv(['a,b', '', '  ', '1,2', '']) == [['a', 'b'], ['1', '2']]


def test_parse_csv_tsv():
    assert aatable.parse_csv(['a\tb', '1\t2'], delimiter='\t') == [['a', 'b'], ['1', '2']]


def test_parse_csv_quoted_field_with_comma():
    # RFC 4180: a comma inside a quoted field is not a delimiter.
    # Without csv.reader honouring quotes, "x,y" would split into 3 cells.
    assert aatable.parse_csv(['a,b', '"x,y",z']) == [['a', 'b'], ['x,y', 'z']]
