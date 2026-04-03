#!/usr/bin/env python3
"""
aacalibrate — Probe terminal character widths by measuring cursor position.

Outputs a JSON profile that aatable.py and other tools can use to
determine the exact display width of characters in the current terminal.

Usage:
    python3 aacalibrate.py                  # interactive probe
    python3 aacalibrate.py --output profile.json
    python3 aacalibrate.py --quick          # probe only Ambiguous category

The probe works by:
  1. Writing a test character to the terminal
  2. Querying cursor position via ANSI escape \\033[6n
  3. Comparing the position to determine rendered width
  4. Saving results as a reusable JSON profile
"""

import sys
import os
import json
import tty
import termios
import unicodedata
import argparse
import re
from typing import Dict, Optional, Tuple


# ─────────────────────────────────────────────
# Terminal cursor position probing
# ─────────────────────────────────────────────

def get_cursor_position(fd: int) -> Optional[Tuple[int, int]]:
    """Query terminal cursor position via ANSI DSR (Device Status Report).

    Sends \\033[6n, reads response \\033[row;colR.
    Returns (row, col) 1-indexed, or None on failure.
    """
    try:
        # Send DSR query
        os.write(fd, b'\033[6n')

        # Read response: \033[row;colR
        buf = b''
        while True:
            ch = os.read(fd, 1)
            buf += ch
            if ch == b'R':
                break
            if len(buf) > 32:
                return None

        match = re.search(rb'\033\[(\d+);(\d+)R', buf)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None
    except Exception:
        return None


def measure_char_width(char: str, fd_in: int, fd_out: int) -> Optional[int]:
    """Measure the actual rendered width of a character in the terminal.

    Returns the number of columns the character occupies, or None on failure.
    """
    # Move to a known position (beginning of a fresh line)
    os.write(fd_out, b'\r\033[K')  # carriage return + clear line

    # Get baseline position
    pos_before = get_cursor_position(fd_in)
    if pos_before is None:
        return None

    # Write the test character
    os.write(fd_out, char.encode('utf-8'))

    # Get new position
    pos_after = get_cursor_position(fd_in)
    if pos_after is None:
        return None

    # Clean up
    os.write(fd_out, b'\r\033[K')

    # Width = column difference
    width = pos_after[1] - pos_before[1]
    return max(0, width)


# ─────────────────────────────────────────────
# Test character sets
# ─────────────────────────────────────────────

# Representative characters for each EAW category
PROBE_CHARS_FULL = {
    # Category: (char, name, expected_eaw)
    'wide_cjk': [
        ('あ', 'Hiragana A', 'W'),
        ('漢', 'Kanji', 'W'),
        ('가', 'Hangul GA', 'W'),
    ],
    'fullwidth': [
        ('Ａ', 'Fullwidth A', 'F'),
        ('１', 'Fullwidth 1', 'F'),
    ],
    'halfwidth': [
        ('ｱ', 'Halfwidth Katakana A', 'H'),
    ],
    'narrow': [
        ('A', 'Latin A', 'Na'),
        ('1', 'Digit 1', 'Na'),
    ],
    'ambiguous': [
        ('①', 'Circled Digit 1', 'A'),
        ('②', 'Circled Digit 2', 'A'),
        ('α', 'Greek Alpha', 'A'),
        ('β', 'Greek Beta', 'A'),
        ('γ', 'Greek Gamma', 'A'),
        ('—', 'Em Dash', 'A'),
        ('―', 'Horizontal Bar', 'A'),
        ('‐', 'Hyphen', 'A'),
        ('♠', 'Black Spade Suit', 'A'),
        ('♥', 'Black Heart Suit', 'A'),
        ('♣', 'Black Club Suit', 'A'),
        ('√', 'Square Root', 'A'),
        ('∞', 'Infinity', 'A'),
        ('≧', 'Greater-Than Over Equal To', 'A'),
        ('≦', 'Less-Than Over Equal To', 'A'),
        ('÷', 'Division Sign', 'A'),
        ('×', 'Multiplication Sign', 'A'),
        ('°', 'Degree Sign', 'A'),
        ('±', 'Plus-Minus Sign', 'A'),
        ('¥', 'Yen Sign', 'A'),
    ],
    'neutral_symbols': [
        ('♦', 'Black Diamond Suit', 'N'),
        ('★', 'Black Star', 'N'),
    ],
    'emoji': [
        ('😀', 'Grinning Face', 'W'),
        ('🎉', 'Party Popper', 'W'),
        ('🔥', 'Fire', 'W'),
        ('❤', 'Heavy Black Heart', 'A'),
    ],
    'emoji_zwj': [
        ('👨\u200d👩\u200d👧', 'Family MWG (ZWJ)', 'ZWJ'),
        ('👩\u200d💻', 'Woman Technologist (ZWJ)', 'ZWJ'),
    ],
    'regional_indicator': [
        ('\U0001F1EF\U0001F1F5', 'Flag JP', 'RI'),
        ('\U0001F1FA\U0001F1F8', 'Flag US', 'RI'),
    ],
}

PROBE_CHARS_QUICK = {
    'ambiguous': PROBE_CHARS_FULL['ambiguous'],
    'emoji': PROBE_CHARS_FULL['emoji'],
    'emoji_zwj': PROBE_CHARS_FULL['emoji_zwj'],
}


# ─────────────────────────────────────────────
# Profile generation
# ─────────────────────────────────────────────

DEFAULT_PROFILE_PATH = os.path.expanduser('~/.aatable_profile.json')


def generate_profile(
    probe_chars: dict,
    fd_in: int,
    fd_out: int,
    verbose: bool = True,
) -> dict:
    """Probe terminal and generate a width profile."""

    results: Dict[str, list] = {}
    ambiguous_widths = []

    for category, chars in probe_chars.items():
        results[category] = []
        for char, name, expected_eaw in chars:
            measured = measure_char_width(char, fd_in, fd_out)
            entry = {
                'char': char,
                'name': name,
                'codepoints': [f'U+{ord(c):04X}' for c in char],
                'eaw': expected_eaw,
                'measured_width': measured,
            }
            results[category].append(entry)

            if expected_eaw == 'A' and measured is not None:
                ambiguous_widths.append(measured)

            if verbose and measured is not None:
                status = 'OK' if measured > 0 else '??'
                if verbose:
                    # Write status to stderr so it doesn't mix with JSON output
                    sys.stderr.write(f'  {char}  width={measured}  ({name}, EAW={expected_eaw}) {status}\n')

    # Determine ambiguous width consensus
    if ambiguous_widths:
        avg = sum(ambiguous_widths) / len(ambiguous_widths)
        ambiguous_consensus = 2 if avg > 1.5 else 1
    else:
        ambiguous_consensus = 1

    profile = {
        'terminal': detect_terminal(),
        'ambiguous_width': ambiguous_consensus,
        'probe_results': results,
    }

    return profile


def detect_terminal() -> dict:
    """Detect terminal type from environment variables."""
    return {
        'TERM': os.environ.get('TERM', ''),
        'TERM_PROGRAM': os.environ.get('TERM_PROGRAM', ''),
        'WT_SESSION': os.environ.get('WT_SESSION', '') != '',
        'LANG': os.environ.get('LANG', ''),
        'LC_CTYPE': os.environ.get('LC_CTYPE', ''),
        'SSH_TTY': os.environ.get('SSH_TTY', '') != '',
        'WSL_DISTRO_NAME': os.environ.get('WSL_DISTRO_NAME', ''),
    }


def print_summary(profile: dict):
    """Print a human-readable summary to stderr."""
    sys.stderr.write('\n=== AATable Terminal Profile ===\n')

    terminal = profile.get('terminal', {})
    term_name = terminal.get('TERM_PROGRAM') or terminal.get('TERM') or 'unknown'
    if terminal.get('WT_SESSION'):
        term_name += ' (Windows Terminal)'
    if terminal.get('WSL_DISTRO_NAME'):
        term_name += f' / WSL ({terminal["WSL_DISTRO_NAME"]})'

    sys.stderr.write(f'Terminal: {term_name}\n')
    sys.stderr.write(f'Ambiguous width: {profile["ambiguous_width"]}\n\n')

    # Summary table
    for category, entries in profile.get('probe_results', {}).items():
        sys.stderr.write(f'[{category}]\n')
        for entry in entries:
            char = entry['char']
            measured = entry['measured_width']
            name = entry['name']
            if measured is not None:
                sys.stderr.write(f'  {char}\t→ {measured} columns\t({name})\n')
            else:
                sys.stderr.write(f'  {char}\t→ FAILED\t({name})\n')
        sys.stderr.write('\n')


def load_profile(path: str = DEFAULT_PROFILE_PATH) -> Optional[dict]:
    """Load a saved profile from disk."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Probe terminal character widths and generate a width profile.',
        epilog='The profile is saved to ~/.aatable_profile.json by default.',
    )
    parser.add_argument(
        '--output', '-o', default=DEFAULT_PROFILE_PATH,
        help=f'Output profile path (default: {DEFAULT_PROFILE_PATH})',
    )
    parser.add_argument(
        '--quick', '-q', action='store_true',
        help='Quick mode: probe only Ambiguous and emoji characters',
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output profile JSON to stdout (for piping)',
    )
    parser.add_argument(
        '--quiet', action='store_true',
        help='Suppress progress output',
    )

    args = parser.parse_args()

    # Check if we have a terminal
    if not sys.stdin.isatty():
        print('Error: aacalibrate requires an interactive terminal.', file=sys.stderr)
        print('Run it directly, not through a pipe.', file=sys.stderr)
        sys.exit(1)

    fd_in = sys.stdin.fileno()
    fd_out = sys.stdout.fileno()

    # Save terminal settings
    old_settings = termios.tcgetattr(fd_in)

    try:
        # Set terminal to raw mode for cursor position queries
        tty.setraw(fd_in)

        probe_set = PROBE_CHARS_QUICK if args.quick else PROBE_CHARS_FULL

        if not args.quiet:
            sys.stderr.write('Probing terminal character widths...\n\n')

        profile = generate_profile(
            probe_set, fd_in, fd_out,
            verbose=not args.quiet,
        )

    finally:
        # Restore terminal settings
        termios.tcsetattr(fd_in, termios.TCSADRAIN, old_settings)
        # Clear any leftover raw-mode artifacts
        sys.stdout.write('\r\033[K')
        sys.stdout.flush()

    if not args.quiet:
        print_summary(profile)

    # Save profile
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)

    if args.json:
        print(profile_json)
    else:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(profile_json)
        sys.stderr.write(f'Profile saved to: {args.output}\n')
        sys.stderr.write(f'\naatable.py will auto-detect this profile.\n')


if __name__ == '__main__':
    main()
