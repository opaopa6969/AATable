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

1. **Grapheme cluster segmentation** — splits text into visual units, handling ZWJ sequences (`👨‍👩‍👧`) and regional indicators (`🇯🇵`) as single glyphs
2. **East Asian Width lookup** — uses `unicodedata.east_asian_width()` per codepoint
3. **Width-aware padding** — pads with spaces based on calculated display width, not `len()`

## License

MIT
