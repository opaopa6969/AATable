"""Tests for aatable.pad_to_width()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aatable


def test_left_pad_cjk():
    result = aatable.pad_to_width("田中", 8)
    assert result == "田中    "
    assert aatable.display_width(result) == 8


def test_left_pad_ascii():
    result = aatable.pad_to_width("Alice", 8)
    assert result == "Alice   "


def test_right_pad():
    result = aatable.pad_to_width("田中", 8, "right")
    assert result == "    田中"


def test_center_pad():
    result = aatable.pad_to_width("abc", 6, "center")
    assert len(result) >= 6  # centered with padding


def test_no_truncation_when_too_wide():
    # text wider than target: should still return the text unchanged or at minimum untruncated
    result = aatable.pad_to_width("ab", 1)
    assert "ab" in result
