# Changelog

All notable changes to AATable are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [0.4.0] - 2025-01-01

### Added
- `aacalibrate.py` — interactive terminal probe that measures actual character widths via ANSI cursor-position queries and saves `~/.aatable_profile.json`
- `aatable.py` auto-loads `~/.aatable_profile.json` at startup; `--ambiguous-width` overrides the profile
- Quick mode (`--quick`) for `aacalibrate.py`: probes only Ambiguous and emoji characters

---

## [0.3.0] - 2025-01-01

### Added
- `mmd2ge.py` — Mermaid flowchart → Graph::Easy format converter with zero-width space (U+200B) CJK width trick
- `aafixwidth.py` — post-processor to fix CJK width misalignment in existing ASCII Art
- CSV and TSV input support in `aatable.py` (`-f csv`, `-f tsv`)
- Auto-detection of input format (Markdown / TSV / CSV)
- Explanation of zero-width space approach in README

---

## [0.2.0] - 2025-01-01

### Added
- Five box-drawing styles: `single`, `double`, `bold`, `round`, `ascii`
- `--style` / `-s` option
- `--demo` flag: shows all character types and all styles
- `--no-header` flag: first row treated as data, not header

---

## [0.1.0] - 2025-01-01

### Added
- Initial release: `aatable.py` — Markdown table → ASCII Art table converter
- Grapheme cluster segmentation (ZWJ sequences, regional indicator flag pairs, skin-tone modifiers)
- East Asian Width calculation via `unicodedata.east_asian_width()`
- `pad_to_width()`: spaces-based padding using `display_width()`, not `len()`
- `--ambiguous-width` / `-a` option: `1` for Windows Terminal (default), `2` for macOS Terminal.app
- `--padding` / `-p` option: configurable cell padding
