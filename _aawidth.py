"""
Shared display-width utilities for aatable.py and aafixwidth.py.

Provides grapheme-cluster-aware East Asian Width calculation so that
ZWJ emoji and modified emoji sequences are not over-counted.
"""

import unicodedata
import json
import os
from contextvars import ContextVar
from typing import List

# ─────────────────────────────────────────────
# Ambiguous-width context (1 = narrow, 2 = wide)
# ─────────────────────────────────────────────

_PROFILE_PATH = os.path.expanduser('~/.aatable_profile.json')

_ambiguous_width: ContextVar[int] = ContextVar(
    'ambiguous_width', default=1
)


def load_ambiguous_width_from_profile() -> int:
    """Load ambiguous_width from aacalibrate profile if available."""
    try:
        with open(_PROFILE_PATH, 'r', encoding='utf-8') as f:
            profile = json.load(f)
            return int(profile.get('ambiguous_width', 1))
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
        return 1


def set_ambiguous_width(value: int) -> None:
    """Set the current context's ambiguous width used by display_width()."""
    _ambiguous_width.set(value)


def get_ambiguous_width() -> int:
    return _ambiguous_width.get()


# ─────────────────────────────────────────────
# Grapheme cluster segmentation
# ─────────────────────────────────────────────

ZWJ = '‍'   # U+200D Zero Width Joiner
VS15 = '︎'  # U+FE0E Variation Selector-15 (text presentation)
VS16 = '️'  # U+FE0F Variation Selector-16 (emoji presentation)


def _is_regional_indicator(cp: int) -> bool:
    return 0x1F1E6 <= cp <= 0x1F1FF


def _is_emoji_modifier(cp: int) -> bool:
    return 0x1F3FB <= cp <= 0x1F3FF


def _is_emoji_base(cp: int) -> bool:
    """Rough check: is this codepoint likely an emoji that can start a ZWJ/modifier sequence?"""
    return (
        0x1F600 <= cp <= 0x1F64F   # emoticons
        or 0x1F900 <= cp <= 0x1F9FF  # supplemental symbols
        or 0x1FA00 <= cp <= 0x1FA6F  # chess symbols
        or 0x1FA70 <= cp <= 0x1FAFF  # symbols extended-A
        or 0x2600 <= cp <= 0x27BF    # misc symbols, dingbats
        or 0x1F300 <= cp <= 0x1F5FF  # misc symbols & pictographs
        or 0x1F680 <= cp <= 0x1F6FF  # transport & map
        or 0x1F1E0 <= cp <= 0x1F1FF  # regional indicators
        or cp in (0x2640, 0x2642, 0x2695, 0x2696, 0x2708, 0x2764)  # common joiners
    )


def split_grapheme_clusters(text: str) -> List[str]:
    """Split text into grapheme clusters, handling ZWJ sequences and regional indicators.

    Not a full UAX #29 implementation, but covers the main emoji cases that
    cause width miscalculation:
      - ZWJ sequences:  👨‍👩‍👧  (man + ZWJ + woman + ZWJ + girl)
      - Regional pairs:  🇯🇵  (J + P regional indicators)
      - Modifier sequences:  👋🏽  (hand + skin tone)
      - Variation selectors:  ☺️  (base + VS16)
    """
    clusters: List[str] = []
    codepoints = [ord(ch) for ch in text]
    i = 0
    n = len(codepoints)

    while i < n:
        cp = codepoints[i]
        start = i
        i += 1

        # Regional indicator pair → single cluster
        if _is_regional_indicator(cp) and i < n and _is_regional_indicator(codepoints[i]):
            i += 1
            clusters.append(text[start:i])
            continue

        # Emoji / ZWJ sequence: consume ZWJ chains, modifiers, variation selectors
        if _is_emoji_base(cp):
            while i < n:
                nxt = codepoints[i]
                if nxt == ord(ZWJ) and i + 1 < n:
                    i += 2  # skip ZWJ + next codepoint
                elif nxt == ord(VS15) or nxt == ord(VS16):
                    i += 1
                elif _is_emoji_modifier(nxt):
                    i += 1
                elif unicodedata.category(chr(nxt)) in ('Mn', 'Me'):
                    i += 1
                else:
                    break
            clusters.append(text[start:i])
            continue

        # Regular character: consume following combining marks and variation selectors
        while i < n:
            nxt = codepoints[i]
            cat = unicodedata.category(chr(nxt))
            if cat in ('Mn', 'Me') or nxt == ord(VS15) or nxt == ord(VS16):
                i += 1
            else:
                break
        clusters.append(text[start:i])

    return clusters


# ─────────────────────────────────────────────
# Display width calculation (East Asian Width)
# ─────────────────────────────────────────────

def _single_char_width(ch: str) -> int:
    """Width of a single codepoint (internal helper)."""
    cp = ord(ch)
    cat = unicodedata.category(ch)
    # Zero-width characters: combining marks, format characters
    # (ZWSP/ZWJ/ZWNJ/bidi marks — but not SOFT HYPHEN, which terminals
    # render as a visible hyphen), Hangul jamo medial vowels / final
    # consonants (composed into the preceding syllable), and line/para
    # separators. Terminals advance the cursor 0 columns for these.
    if cat in ('Mn', 'Me'):
        return 0
    if cat == 'Cf' and cp != 0x00AD:
        return 0
    if 0x1160 <= cp <= 0x11FF or cp in (0x2028, 0x2029):
        return 0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ('W', 'F'):
        return 2
    if eaw == 'A':
        return _ambiguous_width.get()
    return 1


def grapheme_width(cluster: str) -> int:
    """Return the display width of a grapheme cluster.

    A grapheme cluster that contains ZWJ or regional indicators is
    rendered as a single glyph of width 2 by modern terminals.
    """
    if len(cluster) == 1:
        return _single_char_width(cluster)

    codepoints = [ord(ch) for ch in cluster]

    # ZWJ sequence → single emoji glyph → width 2
    if ord(ZWJ) in codepoints:
        return 2

    # Regional indicator pair → single flag emoji → width 2
    if len(codepoints) >= 2 and _is_regional_indicator(codepoints[0]):
        return 2

    # Emoji + modifier (skin tone) → width 2
    if _is_emoji_base(codepoints[0]):
        return 2

    # Base char + combining marks → width of base
    return _single_char_width(cluster[0])


def display_width(text: str) -> int:
    """Return the display width of a string in monospace columns."""
    return sum(grapheme_width(cluster) for cluster in split_grapheme_clusters(text))
