[日本語版](getting-started-ja.md)

# Getting Started

---

## Requirements

- Python 3.8 or later (stdlib only — no pip install)
  - Python 3.8 reached end-of-life in October 2024. Python 3.9+ is recommended.
- For `mmd2ge.py`: [Graph::Easy](https://metacpan.org/pod/Graph::Easy) Perl module
- For `aacalibrate.py`: an interactive TTY (cannot be piped)

---

## Installation

```bash
git clone https://github.com/opaopa6969/AATable.git
cd AATable
chmod +x aatable.py aafixwidth.py mmd2ge.py aacalibrate.py
```

No virtual environment, no dependencies, no build step.

To install Graph::Easy for Mermaid flowchart support:

```bash
cpanm Graph::Easy       # via cpanminus
# or
perl -MCPAN -e 'install Graph::Easy'
```

---

## First Steps

### 1. Verify Python version

```bash
python3 --version
# Python 3.9.x or later recommended
```

### 2. Run the built-in demo

```bash
python3 aatable.py --demo
```

You should see a table with mixed ASCII, CJK, fullwidth, halfwidth, Ambiguous, and emoji characters, followed by the same data in all five box styles.

### 3. Pipe a Markdown table

```bash
echo '| name     | age | city     |
|----------|-----|----------|
| 田中太郎 | 30  | 東京     |
| Alice    | 25  | New York |
| 鈴木①    | 42  | 大阪     |' | python3 aatable.py
```

Expected output:

```
┌──────────┬─────┬──────────┐
│ name     │ age │ city     │
├──────────┼─────┼──────────┤
│ 田中太郎 │ 30  │ 東京     │
├──────────┼─────┼──────────┤
│ Alice    │ 25  │ New York │
├──────────┼─────┼──────────┤
│ 鈴木①   │ 42  │ 大阪     │
└──────────┴─────┴──────────┘
```

### 4. Calibrate your terminal (optional but recommended)

If your terminal renders `①` or `α` as double-width, run this once:

```bash
python3 aacalibrate.py --quick
```

After calibration, `aatable.py` auto-detects the correct `--ambiguous-width` on every run.

---

## Core Workflow: aatable.py

### Markdown input

```bash
# from stdin
cat table.md | python3 aatable.py

# from file
python3 aatable.py table.md
```

### CSV input

```bash
python3 aatable.py -f csv data.csv
cat data.csv | python3 aatable.py -f csv
```

### TSV input

```bash
python3 aatable.py -f tsv data.tsv
cat data.tsv | python3 aatable.py -f tsv
```

### Auto-detect (default)

```bash
cat anything | python3 aatable.py
# Tries Markdown → TSV → CSV in order
```

### Styles

```bash
python3 aatable.py --style double data.csv
python3 aatable.py --style bold   data.csv
python3 aatable.py --style round  data.csv
python3 aatable.py --style ascii  data.csv
```

### macOS Terminal (Ambiguous = 2)

```bash
python3 aatable.py --ambiguous-width 2 data.md
# Or: run aacalibrate.py once, then omit the flag
```

---

## Workflow: mmd2ge.py + graph-easy

Convert Mermaid flowcharts to ASCII Art with proper CJK box sizing.

### Basic pipeline

```bash
cat flow.mmd | python3 mmd2ge.py | graph-easy --as=boxart
```

### With a file

```bash
python3 mmd2ge.py flow.mmd | graph-easy --as=boxart
```

### Example Mermaid input

```
graph LR
A[入力] --> B[パース]
B --> C{判定}
C -->|OK| D[出力]
C -->|NG| E[エラー]
```

```bash
echo 'graph LR
A[入力] --> B[パース]
B --> C{判定}
C -->|OK| D[出力]
C -->|NG| E[エラー]' | python3 mmd2ge.py | graph-easy --as=boxart
```

---

## Workflow: aafixwidth.py

Fix CJK width misalignment in ASCII Art you already have.

```bash
# Fix output from graph-easy directly
graph-easy input.dot | python3 aafixwidth.py

# Fix a saved file
python3 aafixwidth.py broken-aa.txt

# Fix stdin
cat broken-aa.txt | python3 aafixwidth.py
```

---

## Real-World Pipelines

### PostgreSQL

```bash
psql --csv -c "SELECT name, score FROM leaderboard ORDER BY score DESC LIMIT 10" mydb \
  | python3 aatable.py -f csv --style round
```

### git log

```bash
git log --format='%h,%s,%an,%ar' -10 \
  | python3 aatable.py -f csv
```

### docker ps

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' \
  | python3 aatable.py -f tsv --style bold --no-header
```

### curl + jq

```bash
curl -s https://api.example.com/users \
  | jq -r '["id","name","email"], (.[] | [(.id|tostring),.name,.email]) | @csv' \
  | python3 aatable.py -f csv
```

---

## Troubleshooting

### Columns misalign in macOS Terminal.app

macOS Terminal renders Ambiguous-width characters (`①`, `α`, `♠`, etc.) at width 2.  
Run calibration or add the flag:

```bash
python3 aacalibrate.py --quick
# or
python3 aatable.py --ambiguous-width 2 data.md
```

### `graph-easy: command not found`

Install Graph::Easy:

```bash
cpanm Graph::Easy
```

If `cpanm` is not available:

```bash
curl -L https://cpanmin.us | perl - Graph::Easy
```

### Emoji still looks wrong

Some terminals (especially older ones) do not support ZWJ sequences or regional indicator pairs as single glyphs. The output of `aatable.py` is correct for terminals that render them as one glyph. If your terminal renders them differently, the display will be off regardless of what AATable does — this is a terminal limitation, not a bug.

### aacalibrate.py fails with "requires an interactive terminal"

`aacalibrate.py` writes to and reads from the TTY directly. It cannot be piped. Run it directly in your terminal emulator, not inside a script.
