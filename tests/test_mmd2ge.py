"""Tests for mmd2ge.pad_for_grapheasy() and Ambiguous width handling."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import mmd2ge
import _aawidth


@pytest.fixture(autouse=True)
def _restore_ambiguous_width():
    """Restore the global Ambiguous width after each test to avoid leaking
    state into sibling test modules that share the _aawidth module."""
    original = _aawidth.get_ambiguous_width()
    yield
    _aawidth.set_ambiguous_width(original)


def test_pad_len_matches_display_width_amb1():
    _aawidth.set_ambiguous_width(1)
    label = '判定①'
    padded = mmd2ge.pad_for_grapheasy(label)
    assert len(padded) == _aawidth.display_width(label)


def test_pad_len_matches_display_width_amb2():
    _aawidth.set_ambiguous_width(2)
    label = '判定①'
    padded = mmd2ge.pad_for_grapheasy(label)
    assert len(padded) == _aawidth.display_width(label)


def test_ambiguous_char_gets_zwsp_only_when_width2():
    # Ambiguous '①' is width 1 under amb=1 (no ZWSP) and width 2 under amb=2 (ZWSP added).
    _aawidth.set_ambiguous_width(1)
    p1 = mmd2ge.pad_for_grapheasy('①')
    _aawidth.set_ambiguous_width(2)
    p2 = mmd2ge.pad_for_grapheasy('①')
    assert p1.count('\u200b') == 0
    assert p2.count('\u200b') == 1


def test_wide_chars_always_padded():
    for amb in (1, 2):
        _aawidth.set_ambiguous_width(amb)
        padded = mmd2ge.pad_for_grapheasy('漢')
        assert len(padded) == _aawidth.display_width('漢')
        assert padded.endswith('\u200b')


def test_forward_reference_resolves_label():
    # Issue #34: node definitions after edges (forward references) must
    # resolve to their labels, and standalone defs must not be duplicated.
    lines = ['graph LR', 'A --> B', 'A[Start]', 'B[End]']
    _, ge_lines, _ = mmd2ge.parse_mermaid(lines)
    assert any('[ Start ] --> [ End ]' in l for l in ge_lines)
    assert not any('[ A ]' in l for l in ge_lines)
    assert not any('[ B ]' in l for l in ge_lines)
    assert not any(l.strip() == '[ Start ]' for l in ge_lines)
    assert not any(l.strip() == '[ End ]' for l in ge_lines)


def test_backward_reference_unchanged():
    # Backward reference (definition before edge) must still work.
    lines = ['graph LR', 'A[Start] --> B[End]']
    _, ge_lines, _ = mmd2ge.parse_mermaid(lines)
    assert any('[ Start ] --> [ End ]' in l for l in ge_lines)


def test_orphan_node_still_emitted():
    # A standalone node not referenced by any edge must still be emitted.
    lines = ['graph TD', 'A[Start] --> B[End]', 'C[Foo]']
    _, ge_lines, _ = mmd2ge.parse_mermaid(lines)
    assert any('[ Start ] --> [ End ]' in l for l in ge_lines)
    assert any(l.strip() == '[ Foo ]' for l in ge_lines)
