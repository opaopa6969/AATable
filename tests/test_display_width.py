"""Tests for aatable.display_width()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aatable


def test_empty_string():
    assert aatable.display_width("") == 0


def test_ascii():
    assert aatable.display_width("Hello") == 5


def test_cjk_kanji():
    assert aatable.display_width("漢字") == 4


def test_fullwidth():
    assert aatable.display_width("Ａ１") == 4


def test_halfwidth_kana():
    assert aatable.display_width("ｱｲｳ") == 3


def test_emoji_single():
    assert aatable.display_width("😀") == 2


def test_zwj_sequence():
    assert aatable.display_width("👨‍👩‍👧") == 2


def test_regional_indicator_pair():
    assert aatable.display_width("🇯🇵") == 2


def test_skin_tone_modifier():
    assert aatable.display_width("👋🏽") == 2


def test_mixed_ascii_cjk():
    # "Hello" (5) + "世界" (4 wide) + "!" (1) = 10
    assert aatable.display_width("Hello世界!") == 10


def test_name():
    assert aatable.display_width("田中太郎") == 8


def test_ambiguous_width_1():
    original = aatable._ambiguous_width
    aatable._ambiguous_width = 1
    assert aatable.display_width("①②③") == 3
    aatable._ambiguous_width = original


def test_ambiguous_width_2():
    original = aatable._ambiguous_width
    aatable._ambiguous_width = 2
    assert aatable.display_width("①②③") == 6
    aatable._ambiguous_width = original
