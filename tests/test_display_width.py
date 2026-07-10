"""Tests for aatable.display_width()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import aatable
import _aawidth as _aawidth_mod


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
    original = _aawidth_mod.get_ambiguous_width()
    _aawidth_mod.set_ambiguous_width(1)
    assert aatable.display_width("①②③") == 3
    _aawidth_mod.set_ambiguous_width(original)


def test_ambiguous_width_2():
    original = _aawidth_mod.get_ambiguous_width()
    _aawidth_mod.set_ambiguous_width(2)
    assert aatable.display_width("①②③") == 6
    _aawidth_mod.set_ambiguous_width(original)


def test_zero_width_space():
    # mmd2ge inserts U+200B after wide chars so graph-easy's len()
    # matches display width; terminals advance 0 columns for it.
    assert aatable.display_width("入\u200b力\u200b") == 4


def test_zero_width_space_alone():
    assert aatable.display_width("\u200b") == 0


def test_zero_width_joiner_alone():
    assert aatable.display_width("\u200d") == 0


def test_combining_dakuten_alone():
    assert aatable.display_width("\u3099") == 0


def test_combining_handakuten_cluster():
    # ハ + combining handakuten renders as パ: one 2-column glyph
    assert aatable.display_width("ハ\u309a") == 2


def test_soft_hyphen_is_visible():
    # U+00AD renders as a visible hyphen in terminals (width 1)
    assert aatable.display_width("\u00ad") == 1
