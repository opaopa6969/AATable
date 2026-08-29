"""Tests for aatable.render_aa_table()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aatable


def test_consistent_row_widths():
    rows = [["name", "val"], ["田中", "1"]]
    result = aatable.render_aa_table(rows)
    lines = [line for line in result.split('\n') if line]
    widths = [aatable.display_width(line) for line in lines]
    assert len(set(widths)) == 1, f"Inconsistent widths: {widths}"


def test_output_is_string():
    rows = [["a", "b"], ["1", "2"]]
    result = aatable.render_aa_table(rows)
    assert isinstance(result, str)


def test_cjk_table_nonempty():
    rows = [["名前", "得点"], ["田中太郎", "95"]]
    result = aatable.render_aa_table(rows)
    assert "田中太郎" in result
    assert "得点" in result


def test_ragged_rows_normalized():
    # Rows with unequal column counts must be padded so that render_aa_table
    # does not crash and every output line stays the same display width.
    rows = [["a", "b", "c"], ["1"]]
    result = aatable.render_aa_table(rows)
    lines = [line for line in result.split('\n') if line]
    widths = [aatable.display_width(line) for line in lines]
    assert len(set(widths)) == 1, f"Ragged rows produced inconsistent widths: {widths}"


def test_all_styles_uniform_width():
    # Every style's box chars must be single-column; a multi-column box
    # char or broken h_line math would silently misalign the table.
    rows = [["名前", "値"], ["田中", "95"], ["ABC", "①②"]]
    for style in aatable.STYLES:
        result = aatable.render_aa_table(rows, style_name=style)
        lines = [line for line in result.split('\n') if line]
        widths = [aatable.display_width(line) for line in lines]
        assert len(set(widths)) == 1, f"style={style} inconsistent: {widths}"
