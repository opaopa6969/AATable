# AATable

Convert tabular data (Markdown / CSV / TSV) to beautifully aligned ASCII Art tables in your terminal.

Properly handles **CJK characters**, **East Asian Ambiguous width**, **emoji**, **ZWJ sequences**, and **flag emoji** so columns actually align in monospace terminals.

## Demo

```
╭────────────┬─────┬──────────╮
│ name       │ age │ city     │
├────────────┼─────┼──────────┤
│ 田中太郎   │ 30  │ 東京     │
├────────────┼─────┼──────────┤
│ John Smith │ 25  │ New York │
├────────────┼─────┼──────────┤
│ 鈴木①      │ 42  │ 大阪     │
╰────────────┴─────┴──────────╯
```

## Install

```bash
# No dependencies — just Python 3.8+
git clone https://github.com/opaopa6969/AATable.git
cd AATable
chmod +x aatable.py
```

## Usage

```bash
# Markdown table
echo '| a | b |
|---|---|
| 1 | 2 |' | python3 aatable.py

# CSV
cat data.csv | python3 aatable.py -f csv

# TSV (e.g. from psql, cut, awk)
cat data.tsv | python3 aatable.py -f tsv

# Auto-detect format (default)
cat anything | python3 aatable.py

# Choose style
cat data.csv | python3 aatable.py -f csv --style bold

# File input
python3 aatable.py input.md

# Demo with all styles
python3 aatable.py --demo
```

## Unix Way

Pipe anything into it:

```bash
# PostgreSQL → table
psql --csv -c "SELECT * FROM users LIMIT 10" mydb | python3 aatable.py -f csv

# git log → table
git log --format='%h,%s,%an' -5 | python3 aatable.py -f csv --style round

# curl + jq → table
curl -s https://api.example.com/data \
  | jq -r '["id","name"], (.[] | [.id,.name]) | @csv' \
  | python3 aatable.py -f csv

# docker ps → table
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' \
  | python3 aatable.py -f tsv --style bold --no-header
```

## Mermaid Flowchart → ASCII Art

Convert Mermaid flowcharts to ASCII art via [Graph::Easy](https://metacpan.org/pod/Graph::Easy):

```bash
# Install Graph::Easy (one time)
cpanm Graph::Easy

# Mermaid → ASCII art pipeline
echo 'graph LR
A[入力] --> B[パース]
B --> C{判定}
C -->|OK| D[出力]
C -->|NG| E[エラー]' | python3 mmd2ge.py | graph-easy --as=boxart
```

Output:

```
               ┌────────┐
               │  入力   │
               └────────┘
                 │
                 ∨
               ┌────────┐
               │ パース  │
               └────────┘
                 │
                 ∨
┌──────┐  OK   ┌────────┐
│ 出力  │ <──── │  判定   │
└──────┘       └────────┘
                 │ NG
                 ∨
               ┌────────┐
               │ エラー  │
               └────────┘
```

**How it works**: `mmd2ge.py` inserts zero-width spaces (U+200B) after CJK characters so that `len()` equals `display_width()`. This tricks Graph::Easy into allocating correctly-sized boxes without any patches to Graph::Easy itself.

### Pipeline tools

| Tool | Role |
|------|------|
| `aatable.py` | Markdown/CSV/TSV → ASCII Art table |
| `mmd2ge.py` | Mermaid → Graph::Easy format (with CJK width fix) |
| `aafixwidth.py` | Post-processor for fixing CJK width in existing AA |

## Box-Drawing Styles

| Style | Preview |
|-------|---------|
| `single` (default) | `┌─┬─┐ │ │ │ └─┴─┘` |
| `double` | `╔═╦═╗ ║ ║ ║ ╚═╩═╝` |
| `bold` | `┏━┳━┓ ┃ ┃ ┃ ┗━┻━┛` |
| `round` | `╭─┬─╮ │ │ │ ╰─┴─╯` |
| `ascii` | `+-+-+ \| \| \| +-+-+` |

## CJK Width Handling

The core challenge of terminal table alignment with mixed scripts:

| Character Type | Example | Width | Unicode EAW |
|---------------|---------|-------|-------------|
| ASCII | `Hello` | 1 per char | Na (Narrow) |
| CJK | `漢字` | 2 per char | W (Wide) |
| Fullwidth | `Ａ１` | 2 per char | F (Fullwidth) |
| Halfwidth Kana | `ｱｲｳ` | 1 per char | H (Halfwidth) |
| Ambiguous | `①α♠` | **terminal-dependent** | A (Ambiguous) |
| Emoji | `😀🎉` | 2 per glyph | W (Wide) |
| ZWJ Sequence | `👨‍👩‍👧` | 2 (1 glyph) | Grapheme cluster |
| Flag | `🇯🇵` | 2 (1 glyph) | Regional Indicator pair |

### Ambiguous Width

The `--ambiguous-width` (`-a`) flag controls how Unicode "Ambiguous" characters are measured:

- **`-a 1`** (default): Correct for **Windows Terminal**, **VS Code**, most modern terminals
- **`-a 2`**: Correct for **macOS Terminal.app**, **iTerm2** (CJK locale)

## Options

```
usage: aatable.py [-h] [--format {auto,md,csv,tsv}]
                  [--style {single,double,bold,ascii,round}]
                  [--padding PADDING] [--no-header]
                  [--ambiguous-width {1,2}] [--demo]
                  [file]

positional arguments:
  file                  Input file (default: stdin)

options:
  -f, --format          Input format (default: auto-detect)
  -s, --style           Box-drawing style (default: single)
  -p, --padding         Cell padding in spaces (default: 1)
  --no-header           Do not treat first row as header
  -a, --ambiguous-width Display width for Ambiguous chars (default: 1)
  --demo                Show demo table
```

## How It Works

### aatable.py (table rendering)

1. **Grapheme cluster segmentation** — splits text into visual units, handling ZWJ sequences (`👨‍👩‍👧`) and regional indicators (`🇯🇵`) as single glyphs
2. **East Asian Width lookup** — uses `unicodedata.east_asian_width()` per codepoint
3. **Width-aware padding** — pads with spaces based on calculated display width, not `len()`

### mmd2ge.py (the zero-width space trick)

Graph::Easy is a fantastic Perl tool that handles graph layout and ASCII art rendering. But like most non-CJK-aware tools, it uses `len()` (character count) to determine box widths. A CJK character like `入` is 1 char but 2 columns wide in a terminal, so boxes come out too narrow:

```
+----+       ← len("入力") = 2, so border is 2+2 padding = 4 dashes
| 入力 |     ← but "入力" renders as 4 columns wide. Overflow!
+----+
```

**The fix**: insert zero-width spaces (U+200B) after each wide character. U+200B is invisible in the terminal but counts toward `len()`:

```python
"入力"           # len=2, display_width=4  ← mismatch!
"入力\u200b\u200b"  # len=4, display_width=4  ← match!
```

Now Graph::Easy sees `len()=4` and allocates a properly-sized box:

```
+------+         ← len=4, so border is 4+2 padding = 6 dashes
| 入力  |        ← 4 columns of CJK + 2 padding. Perfect!
+------+
```

No patches to Graph::Easy required. Pure Unix way: fix the data, not the tool.

### Why not just fix Graph::Easy?

1. It's a CPAN module — patching means forking and maintaining a fork forever
2. The zero-width space trick works with **any** tool that uses `len()` for layout
3. It composes: `mmd2ge.py` is a filter, not a monolith

## The Darkness of Unicode Width

If you've ever tried to align Japanese text in a terminal, you know the pain.

**The core problem**: Unicode defines an "East Asian Width" property for every character, but terminals don't agree on how to render them:

| EAW Category | macOS Terminal | Windows Terminal | The Spec Says |
|--------------|---------------|-----------------|---------------|
| **W** (Wide) | 2 | 2 | 2 |
| **F** (Fullwidth) | 2 | 2 | 2 |
| **Na** (Narrow) | 1 | 1 | 1 |
| **H** (Halfwidth) | 1 | 1 | 1 |
| **A** (Ambiguous) | **2** | **1** | **"depends"** |

The "Ambiguous" category includes `①`, `α`, `♠`, `—` and hundreds of other characters. Unicode literally says the width is ambiguous. Thanks, Unicode.

**Emoji make it worse**: `👨‍👩‍👧` is 7 codepoints (man + ZWJ + woman + ZWJ + girl) but renders as 1 glyph of width 2. `🇯🇵` is 2 codepoints (regional indicators J + P) but also 1 glyph of width 2. You can't calculate display width without understanding grapheme clusters.

**The result**: `len("👨‍👩‍👧") = 7`, but `display_width("👨‍👩‍👧") = 2`. Every tool that uses `len()` for layout will produce garbage. AATable exists because this problem is real and nobody else seems to care.

## License

MIT
