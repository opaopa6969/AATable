[日本語版](architecture-ja.md)

# Architecture

AATable is four Python scripts. Each is a composable Unix filter — it reads from stdin or a file, writes to stdout, and does one thing well.

---

## Script Roles

```
aacalibrate.py   ──→  ~/.aatable_profile.json
                                │
                                ▼
stdin/file  ──→  aatable.py  ──→  stdout   (table rendering)

stdin/file  ──→  mmd2ge.py   ──→  graph-easy  ──→  aafixwidth.py  ──→  stdout
                 (Mermaid→GE)     (layout)         (CJK fix)
```

| Script           | Input               | Output                 | Dependency       |
|------------------|---------------------|------------------------|------------------|
| `aatable.py`     | Markdown/CSV/TSV    | ASCII Art table        | stdlib only      |
| `mmd2ge.py`      | Mermaid flowchart   | Graph::Easy format     | stdlib only      |
| `aafixwidth.py`  | ASCII Art text      | Width-corrected text   | stdlib only      |
| `aacalibrate.py` | Terminal (TTY only) | `~/.aatable_profile.json` | `tty`, `termios` |

All four scripts require **Python 3.8+** (stdlib only, no pip install).  
Python 3.8 reached end-of-life in October 2024; Python 3.9+ is recommended.

---

## Core: `display_width()` and `pad_to_width()`

The fundamental problem AATable solves is that Python's `len()` counts codepoints, not terminal columns.

### `display_width(text: str) -> int`

Located in `aatable.py` (canonical implementation) and duplicated with slight variation in `aafixwidth.py` and `mmd2ge.py`.

Algorithm:

1. Call `split_grapheme_clusters(text)` to split into visual units
2. For each cluster, call `grapheme_width(cluster)`
3. Sum the widths

### `split_grapheme_clusters(text: str) -> List[str]`

A hand-written grapheme cluster segmenter. Not a full UAX #29 implementation, but covers the cases that cause real-world width miscalculation:

| Sequence type          | Example    | Codepoints | Clusters | Width |
|------------------------|------------|------------|----------|-------|
| ASCII                  | `AB`       | 2          | 2        | 2     |
| CJK                    | `漢字`     | 2          | 2        | 4     |
| ZWJ sequence           | `👨‍👩‍👧`    | 7          | 1        | 2     |
| Regional indicator pair | `🇯🇵`    | 2          | 1        | 2     |
| Emoji + skin modifier  | `👋🏽`    | 2          | 1        | 2     |
| Emoji + variation sel. | `☺️`       | 2          | 1        | 2     |

### `grapheme_width(cluster: str) -> int`

Rules applied in order:

1. If the cluster contains U+200D (ZWJ) → width 2 (single emoji glyph)
2. If the first codepoint is a regional indicator → width 2 (flag)
3. If the first codepoint is an emoji base → width 2
4. Otherwise → `unicodedata.east_asian_width()` of the base character

### `pad_to_width(text: str, target_width: int, align: str = 'left') -> str`

Pads `text` with ASCII spaces until its `display_width()` equals `target_width`.

```python
pad_to_width("田中", 8)          # "田中    "  (4 wide chars + 4 spaces = 8)
pad_to_width("Alice", 8)         # "Alice   "  (5 chars + 3 spaces = 8)
pad_to_width("田中", 8, "right") # "    田中"
```

This is the function that makes column alignment work.

---

## East Asian Width and the Ambiguous Problem

Unicode TR11 defines six East Asian Width categories:

| Category   | Width | Notes                                      |
|------------|-------|--------------------------------------------|
| W (Wide)   | 2     | CJK, Hiragana, Katakana, Hangul            |
| F (Fullwidth) | 2  | `Ａ`, `１`, `！`                           |
| Na (Narrow) | 1    | ASCII, Latin                               |
| H (Halfwidth) | 1  | `ｱ`, `ｲ`, `ｳ`                            |
| A (Ambiguous) | **?** | Terminal-dependent; see below          |
| N (Neutral) | 1    | Most symbols not listed above              |

### The Ambiguous category

Unicode literally says Ambiguous width "is context-dependent." Different terminals disagree:

- **Windows Terminal, VS Code terminal, most modern terminals**: width = 1
- **macOS Terminal.app, iTerm2 (CJK locale)**: width = 2

Affected characters include `①②③`, `αβγ`, `♠♥♦♣`, `—`, `±`, `×`, `÷`, `°`.

`aatable.py` defaults to `--ambiguous-width 1`. Use `--ambiguous-width 2` for macOS Terminal, or run `aacalibrate.py` once to auto-detect and persist the setting.

The `_ambiguous_width` module-level variable is set at CLI parse time:

```python
global _ambiguous_width
_ambiguous_width = args.ambiguous_width
```

---

## mmd2ge.py: The Zero-Width Space Trick

Graph::Easy is a CPAN module that computes box widths using Perl's `length()` — equivalent to Python's `len()`. A CJK character is 1 codepoint but 2 terminal columns:

```
Without fix:
+----+       ← length("入力") = 2, so border = 4 (2 + 2 padding)
| 入力 |     ← but "入力" is 4 columns wide → right border at column 5, not 4
+----+
```

The trick: append U+200B (ZERO WIDTH SPACE) after each wide character. U+200B has display width 0 but counts as a character in `len()`:

```python
"入力"              # len=2, display_width=4 — mismatch
"入\u200b力\u200b"  # len=4, display_width=4 — match
```

`pad_for_grapheasy(label)` in `mmd2ge.py` counts wide characters and appends that many U+200B:

```python
def pad_for_grapheasy(label: str) -> str:
    extra = sum(1 for ch in label if char_display_width(ch) == 2)
    return label + '\u200b' * extra
```

This approach composes with any `len()`-based tool, no patches required.

---

## aafixwidth.py: Post-Processing Strategy

For ASCII Art already rendered with wrong widths, `aafixwidth.py` uses a different strategy:

1. **Detect column positions** from horizontal border lines (`+----+----+`)
2. For each content line, split by `|` and measure each segment's `display_width()`
3. Trim trailing spaces equal to `display_width(content) - len(content)` (the "wide character surplus")

This is simpler and more robust than re-rendering from source, because the source may not be available.

### `find_boxes()` — dead code note

`aafixwidth.py` contains a `find_boxes()` function that traces complete rectangular boxes from `+` corners. This function is **not called** in the current implementation — `fix_aa_widths()` uses the simpler `find_column_positions()` approach instead. `find_boxes()` was an earlier design that proved over-engineered for the actual use case. It is preserved for potential future use but is currently unreachable.

---

## aacalibrate.py: Terminal Probing

`aacalibrate.py` requires an interactive TTY (cannot be piped). It:

1. Puts the terminal into raw mode via `tty.setraw()` / `termios`
2. For each test character: moves cursor, writes the character, queries position with ANSI DSR (`\033[6n`), reads `\033[row;colR` response
3. Column delta = rendered width
4. Collects all Ambiguous character measurements, computes consensus (mean > 1.5 → width 2)
5. Saves `{ ambiguous_width: N, probe_results: {...}, terminal: {...} }` to `~/.aatable_profile.json`

`aatable.py` reads the profile at module load time:

```python
_ambiguous_width = _load_ambiguous_width_from_profile()
```

---

## Data Flow Summary

```
Input text
    │
    ▼
split_grapheme_clusters()   — visual unit segmentation
    │
    ▼  (list of clusters)
grapheme_width()            — EAW lookup per cluster
    │
    ▼  (integer width)
pad_to_width()              — space-pad to column width
    │
    ▼  (padded cell string)
render_aa_table()           — assemble box-drawing characters
    │
    ▼
stdout
```
