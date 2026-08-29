"""Tests for aafixwidth.fix_aa_widths()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aafixwidth
from _aawidth import display_width


def _dw_each(text):
    return [display_width(l) for l in text.split('\n')]


def test_already_aligned_aa_not_degraded():
    # Issue #30: input already aligned must stay aligned (non-degrading).
    aa = '+------+\n| 漢字 |\n+------+'
    out = aafixwidth.fix_aa_widths(aa)
    widths = _dw_each(out)
    assert len(set(widths)) == 1, f'widths differ: {widths}'
    assert widths[0] == 8


def test_cjk_overflow_border_extended_to_align():
    # Issue #28: right border must align with content when CJK overflows.
    aa = '+-----+\n| あいう |\n+-----+'
    out = aafixwidth.fix_aa_widths(aa)
    lines = out.split('\n')
    # Compare display widths (visual columns), not string indices, since
    # CJK chars occupy 2 columns but 1 string position.
    widths = _dw_each(out)
    assert len(set(widths)) == 1, f'widths differ: {widths}'
    assert widths[0] == 10


def test_pure_ascii_unchanged():
    aa = '+-----+\n| abc |\n+-----+'
    out = aafixwidth.fix_aa_widths(aa)
    assert out == aa


def test_multicol_cjk_overflow_aligns():
    # Multi-column box: when CJK content overflows a single cell in a
    # multi-column layout, every line's display width must still match
    # (border extended, other cells unchanged).
    aa = '+---+---+\n| あ | B |\n+---+---+'
    out = aafixwidth.fix_aa_widths(aa)
    widths = _dw_each(out)
    assert len(set(widths)) == 1, f'multi-col widths differ: {widths}'
