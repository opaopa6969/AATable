"""Tests for aatable.split_grapheme_clusters()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aatable


def test_ascii_splits():
    assert aatable.split_grapheme_clusters("AB") == ["A", "B"]


def test_cjk_splits():
    assert aatable.split_grapheme_clusters("あ漢") == ["あ", "漢"]


def test_zwj_is_one_cluster():
    assert len(aatable.split_grapheme_clusters("👨‍👩‍👧")) == 1


def test_flag_is_one_cluster():
    assert len(aatable.split_grapheme_clusters("🇯🇵")) == 1


def test_skin_modifier_is_one_cluster():
    assert len(aatable.split_grapheme_clusters("👋🏽")) == 1


def test_empty():
    assert aatable.split_grapheme_clusters("") == []
