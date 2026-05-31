#!/usr/bin/env python3
"""
AATable - Markdown table to ASCII Art table converter.

Properly handles East Asian Width for CJK, fullwidth, and ambiguous characters
so columns align correctly in monospace terminals.

Usage:
    echo '| a | b |' | python3 aatable.py
    python3 aatable.py input.md
    python3 aatable.py --style double input.md
"""

import sys
import csv
import io
import argparse
from typing import List, Optional

# Import shared width utilities (grapheme-cluster-aware East Asian Width)
from _aawidth import (
    display_width,
    grapheme_width,
    split_grapheme_clusters,
    load_ambiguous_width_from_profile,
    set_ambiguous_width,
    get_ambiguous_width,
)
import _aawidth as _aawidth_mod

# Initialise from calibration profile on import
_aawidth_mod.set_ambiguous_width(_aawidth_mod.load_ambiguous_width_from_profile())


def pad_to_width(text: str, target_width: int, align: str = 'left') -> str:
    """Pad text with spaces to reach target display width.

    align: 'left', 'right', or 'center'
    """
    current = display_width(text)
    padding = max(0, target_width - current)

    if align == 'right':
        return ' ' * padding + text
    elif align == 'center':
        left = padding // 2
        right = padding - left
        return ' ' * left + text + ' ' * right
    else:
        return text + ' ' * padding


# ─────────────────────────────────────────────
# Markdown table parsing
# ─────────────────────────────────────────────

def _split_md_row(stripped: str) -> List[str]:
    """Split a Markdown table row on unescaped pipes outside code spans.

    Handles:
      - ``\\|`` — escaped pipe treated as literal '|' inside a cell
      - `` `...` `` — code span: pipes inside backtick spans are not delimiters
    """
    cells: List[str] = []
    current: List[str] = []
    i = 0
    n = len(stripped)

    while i < n:
        ch = stripped[i]

        # Backslash escape: \| → literal '|', any other \X → keep both chars
        if ch == '\\' and i + 1 < n:
            next_ch = stripped[i + 1]
            if next_ch == '|':
                current.append('|')
                i += 2
                continue
            else:
                current.append(ch)
                current.append(next_ch)
                i += 2
                continue

        # Code span: consume from opening backtick(s) to matching closing backtick(s)
        if ch == '`':
            # Count opening backticks
            tick_start = i
            while i < n and stripped[i] == '`':
                i += 1
            fence = stripped[tick_start:i]
            fence_len = len(fence)
            code_start = i
            # Search for matching closing fence (same number of backticks)
            closed = False
            while i < n:
                if stripped[i] == '`':
                    close_start = i
                    while i < n and stripped[i] == '`':
                        i += 1
                    if i - close_start == fence_len:
                        # Found matching close
                        current.append(stripped[tick_start:i])
                        closed = True
                        break
                    # Wrong number of backticks — continue searching
                else:
                    i += 1
            if not closed:
                # Unclosed code span: treat backticks as literal characters
                current.append(stripped[tick_start:i])
            continue

        # Unescaped pipe: cell delimiter
        if ch == '|':
            cells.append(''.join(current))
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    cells.append(''.join(current))
    return cells


def parse_md_table(lines: List[str]) -> Optional[List[List[str]]]:
    """Parse Markdown table lines into a list of rows (list of cell strings).

    Skips the separator row (|---|---|).
    Correctly handles escaped pipes (\\|) and pipes inside code spans (`a|b`).
    Returns None if input is not a valid Markdown table.
    """
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith('|'):
            continue

        # Check if this is a separator row (|---|---|)
        content = stripped.strip('|')
        if all(ch in '-: |' for ch in content):
            continue

        cells = [cell.strip() for cell in _split_md_row(stripped)]
        # Remove empty first/last elements from leading/trailing |
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]

        if cells:
            rows.append(cells)

    return rows if rows else None


def parse_csv(lines: List[str], delimiter: str = ',') -> Optional[List[List[str]]]:
    """Parse CSV/TSV lines into rows.

    Args:
        lines: Input lines.
        delimiter: Field delimiter (',' for CSV, '\\t' for TSV).

    Returns:
        List of rows, or None if empty.
    """
    text = ''.join(lines)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    return rows if rows else None


def parse_auto(lines: List[str]) -> Optional[List[List[str]]]:
    """Auto-detect format (Markdown, TSV, or CSV) and parse.

    Detection order:
      1. If any line starts with '|' → Markdown
      2. If any line contains tab → TSV
      3. Otherwise → CSV
    """
    for line in lines:
        if line.strip().startswith('|'):
            return parse_md_table(lines)

    for line in lines:
        if '\t' in line:
            return parse_csv(lines, delimiter='\t')

    return parse_csv(lines, delimiter=',')


# ─────────────────────────────────────────────
# Box-drawing styles
# ─────────────────────────────────────────────

STYLES = {
    'single': {
        'tl': '\u250c', 'tr': '\u2510', 'bl': '\u2514', 'br': '\u2518',
        'h': '\u2500', 'v': '\u2502',
        'lm': '\u251c', 'rm': '\u2524', 'tm': '\u252c', 'bm': '\u2534',
        'cross': '\u253c',
    },
    'double': {
        'tl': '\u2554', 'tr': '\u2557', 'bl': '\u255a', 'br': '\u255d',
        'h': '\u2550', 'v': '\u2551',
        'lm': '\u2560', 'rm': '\u2563', 'tm': '\u2566', 'bm': '\u2569',
        'cross': '\u256c',
    },
    'bold': {
        'tl': '\u250f', 'tr': '\u2513', 'bl': '\u2517', 'br': '\u251b',
        'h': '\u2501', 'v': '\u2503',
        'lm': '\u2523', 'rm': '\u252b', 'tm': '\u2533', 'bm': '\u253b',
        'cross': '\u254b',
    },
    'ascii': {
        'tl': '+', 'tr': '+', 'bl': '+', 'br': '+',
        'h': '-', 'v': '|',
        'lm': '+', 'rm': '+', 'tm': '+', 'bm': '+',
        'cross': '+',
    },
    'round': {
        'tl': '\u256d', 'tr': '\u256e', 'bl': '\u2570', 'br': '\u256f',
        'h': '\u2500', 'v': '\u2502',
        'lm': '\u251c', 'rm': '\u2524', 'tm': '\u252c', 'bm': '\u2534',
        'cross': '\u253c',
    },
}

# Header separator uses single-line even in bold/double styles
HEADER_SEP_STYLES = {
    'single': 'single',
    'double': 'double',
    'bold': 'bold',
    'ascii': 'ascii',
    'round': 'round',
}


# ─────────────────────────────────────────────
# ASCII Art table rendering
# ─────────────────────────────────────────────

def render_aa_table(
    rows: List[List[str]],
    style_name: str = 'single',
    padding: int = 1,
    header: bool = True,
    align: str = 'left',
) -> str:
    """Render rows as an ASCII art table with proper width calculation.

    Args:
        rows: List of rows, each row is a list of cell strings.
        style_name: Box-drawing style name.
        padding: Spaces inside each cell on each side.
        header: If True, first row is rendered as a header with separator.
        align: Cell text alignment: 'left', 'right', or 'center'.

    Returns:
        Multi-line string of the rendered table.
    """
    if not rows:
        return ''

    style = STYLES.get(style_name, STYLES['single'])

    # Normalize column count (pad short rows)
    max_cols = max(len(row) for row in rows)
    normalized = [row + [''] * (max_cols - len(row)) for row in rows]

    # Calculate column widths (display width)
    col_widths = [0] * max_cols
    for row in normalized:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], display_width(cell))

    # Build horizontal lines
    def h_line(left: str, mid: str, right: str, fill: str) -> str:
        segments = [fill * (col_widths[i] + padding * 2) for i in range(max_cols)]
        return left + mid.join(segments) + right

    top_line = h_line(style['tl'], style['tm'], style['tr'], style['h'])
    mid_line = h_line(style['lm'], style['cross'], style['rm'], style['h'])
    bot_line = h_line(style['bl'], style['bm'], style['br'], style['h'])

    # Build data rows
    def data_row(row: List[str]) -> str:
        cells = []
        for i, cell in enumerate(row):
            padded = pad_to_width(cell, col_widths[i], align=align)
            cells.append(' ' * padding + padded + ' ' * padding)
        return style['v'] + style['v'].join(cells) + style['v']

    # Assemble
    lines = [top_line]
    for idx, row in enumerate(normalized):
        lines.append(data_row(row))
        if idx == 0 and header and len(normalized) > 1:
            lines.append(mid_line)
        elif idx < len(normalized) - 1:
            lines.append(mid_line)
    lines.append(bot_line)

    return '\n'.join(lines)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Convert tabular data (Markdown/CSV/TSV) to ASCII Art tables with proper CJK alignment.',
        epilog='Examples:\n'
               '  echo "| a | b |" | python3 aatable.py\n'
               '  cat data.csv | python3 aatable.py -f csv\n'
               '  psql --csv -c "SELECT *" | python3 aatable.py -f csv --style bold\n'
               '  cat data.tsv | python3 aatable.py -f tsv\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'file', nargs='?', default=None,
        help='Input file containing Markdown table (default: stdin)',
    )
    parser.add_argument(
        '--format', '-f', choices=['auto', 'md', 'csv', 'tsv'], default='auto',
        help='Input format (default: auto-detect)',
    )
    parser.add_argument(
        '--style', '-s', choices=STYLES.keys(), default='single',
        help='Box-drawing style (default: single)',
    )
    parser.add_argument(
        '--padding', '-p', type=int, default=1,
        help='Cell padding in spaces (default: 1)',
    )
    parser.add_argument(
        '--no-header', action='store_true',
        help='Do not treat first row as header',
    )
    parser.add_argument(
        '--ambiguous-width', '-a', type=int, choices=[1, 2], default=None,
        help='Display width for Ambiguous characters (default: from ~/.aatable_profile.json, or 1 for Windows/WSL; use 2 for macOS Terminal)',
    )
    parser.add_argument(
        '--align', '-A', choices=['left', 'right', 'center'], default='left',
        help='Cell text alignment: left|right|center (default: left)',
    )
    parser.add_argument(
        '--demo', action='store_true',
        help='Show a demo table with various character types',
    )

    args = parser.parse_args()

    # Override Ambiguous width only when explicitly specified via -a/--ambiguous-width;
    # otherwise keep the value already loaded from the calibration profile.
    if args.ambiguous_width is not None:
        _aawidth_mod.set_ambiguous_width(args.ambiguous_width)

    if args.demo:
        demo_rows = [
            ['種類', '文字', '幅', '説明'],
            ['ASCII', 'Hello', '5', 'Half-width'],
            ['全角', 'こんにちは', '10', 'Wide (W)'],
            ['全角英数', 'Ａ１', '4', 'Fullwidth (F)'],
            ['半角カナ', 'ｱｲｳ', '3', 'Halfwidth (H)'],
            ['Ambiguous', '①②③', '6', 'Circled digits (A)'],
            ['Ambiguous', 'α β γ', '7', 'Greek (A)'],
            ['記号', '♠♥♦♣', '8', 'Card suits (A)'],
            ['混在', 'Hello世界!', '11', 'Mixed'],
            ['絵文字', '\U0001f600\U0001f389', '4', 'Emoji (W)'],
        ]
        print(render_aa_table(demo_rows, style_name=args.style, padding=args.padding, align=args.align))

        print()
        print('-- All styles demo --')
        small_rows = [
            ['名前', '値'],
            ['あいう', '123'],
            ['ABC', '①②'],
        ]
        for name in STYLES:
            print(f'\n[{name}]')
            print(render_aa_table(small_rows, style_name=name, padding=args.padding))
        return

    # Read input
    if args.file:
        with open(args.file, encoding='utf-8') as f:
            input_lines = f.readlines()
    else:
        if sys.stdin.isatty():
            print('Paste Markdown table (Ctrl+D to finish):', file=sys.stderr)
        input_lines = sys.stdin.readlines()

    fmt = args.format
    if fmt == 'auto':
        rows = parse_auto(input_lines)
    elif fmt == 'md':
        rows = parse_md_table(input_lines)
    elif fmt == 'csv':
        rows = parse_csv(input_lines, delimiter=',')
    elif fmt == 'tsv':
        rows = parse_csv(input_lines, delimiter='\t')
    else:
        rows = None

    if rows is None:
        print('Error: No valid tabular data found in input.', file=sys.stderr)
        sys.exit(1)

    print(render_aa_table(
        rows,
        style_name=args.style,
        padding=args.padding,
        header=not args.no_header,
        align=args.align,
    ))


if __name__ == '__main__':
    main()
