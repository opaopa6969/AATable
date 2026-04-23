# AATable — 仕様書 (SPEC)

バージョン: 0.4.0  
作成日: 2026-04-19  
対象リポジトリ: opaopa6969/AATable

---

## 目次

1. [概要](#1-概要)
2. [機能仕様](#2-機能仕様)
3. [データ永続化層](#3-データ永続化層)
4. [ステートマシン](#4-ステートマシン)
5. [ビジネスロジック](#5-ビジネスロジック)
6. [API / 外部境界](#6-api--外部境界)
7. [UI](#7-ui)
8. [設定](#8-設定)
9. [依存関係](#9-依存関係)
10. [非機能要件](#10-非機能要件)
11. [テスト戦略](#11-テスト戦略)
12. [デプロイ / 運用](#12-デプロイ--運用)

---

## 1. 概要

### 1.1 プロジェクト目的

AATable は、表形式データ（Markdown / CSV / TSV）を CJK・絵文字・Unicode Ambiguous 文字を含む場合でも正しく列が揃う ASCII Art テーブルへ変換する Python CLI ツール群である。

Python 標準の `len()` は文字コードポイント数を返すが、等幅フォントのターミナルでは漢字・ひらがな・絵文字などが 2 カラム幅を占める。この不一致によって生じる「ボーダーがずれる」「セル内容がはみ出す」「テーブルが崩れる」問題を、`display_width()` 関数で根本的に解決することが主目的である。

具体的には以下の問題を解決する:

```
# 問題: len() ベースのツールが生成する崩れたテーブル
+-----+------+
| 名前 | 得点 |
+-----+------+
| 田中太郎 | 95 |   ← "田中太郎" は len=4 だが表示幅=8
+-----+------+

# AATable が生成する正しいテーブル
┌──────────┬──────┐
│ 名前     │ 得点 │
├──────────┼──────┤
│ 田中太郎 │ 95   │
└──────────┴──────┘
```

### 1.2 対象ユーザー

- CLI ツールの出力（`psql`, `docker ps`, `git log` 等）を整形して表示したいエンジニア
- CJK 文字を含むデータを扱う日本語・中国語・韓国語圏のユーザー
- Mermaid フローチャートを ASCII Art として表示したい開発者
- macOS Terminal.app や Windows Terminal など、Ambiguous 幅の扱いが異なるターミナル環境のユーザー

### 1.3 スコープ

**対象:**
- 4 つの独立した Python スクリプト（`aatable.py`, `aafixwidth.py`, `mmd2ge.py`, `aacalibrate.py`）
- 標準入力またはファイルを受け取り、標準出力へテキストを書く Unix フィルタ設計
- CJK・絵文字・Ambiguous カテゴリ文字の正確な表示幅計算

**対象外:**
- ウェブ UI、GUI、TUI
- Python パッケージ化（`pip install` による配布は未対応）
- データベース連携
- グラフ描画エンジン（Graph::Easy は外部 CPAN モジュール。本ツール群は入力変換のみ担当）
- リアルタイム更新・ストリーミング

### 1.4 設計方針

| 方針 | 説明 |
|------|------|
| Unix フィルタ | stdin → stdout。各スクリプトは一つのことだけを行う |
| 標準ライブラリのみ | `pip install` 不要。`python3` があれば即実行可能 |
| 組み合わせ可能 | パイプでスクリプトを連結できる |
| 型注釈付与 | `typing` モジュールで型注釈を付与。静的解析ツールに対応 |
| エラーは stderr | 整形済みデータは stdout のみ。エラー・プログレスは stderr |

### 1.5 バージョン履歴

| バージョン | 日付 | 主な変更 |
|-----------|------|---------|
| 0.1.0 | 2025-01-01 | 初回リリース。`aatable.py`、グラフェームクラスター分割、EAW 計算、`pad_to_width()` |
| 0.2.0 | 2025-01-01 | 5 種のボックスドローイングスタイル、`--style`, `--demo`, `--no-header` オプション |
| 0.3.0 | 2025-01-01 | `mmd2ge.py`, `aafixwidth.py`、CSV/TSV 入力サポート、自動フォーマット検出 |
| 0.4.0 | 2025-01-01 | `aacalibrate.py`（ターミナルプローブ）、プロファイル自動読み込み、`--align` オプション |

---

## 2. 機能仕様

### 2.1 スクリプト一覧

| スクリプト | 役割 | 入力 | 出力 |
|-----------|------|------|------|
| `aatable.py` | Markdown / CSV / TSV → ASCII Art テーブル | テキスト（表形式） | ASCII Art テーブル |
| `mmd2ge.py` | Mermaid フローチャート → Graph::Easy 形式 | Mermaid 構文 | Graph::Easy 構文 |
| `aafixwidth.py` | 既存 ASCII Art の CJK 幅ずれを修正 | ASCII Art テキスト | 修正済み ASCII Art テキスト |
| `aacalibrate.py` | ターミナル文字幅の実測・プロファイル生成 | TTY（インタラクティブ） | `~/.aatable_profile.json` |

### 2.2 aatable.py

#### 2.2.1 概要

`aatable.py` は表形式データを入力として受け取り、ボックスドローイング文字を使った整形済み ASCII Art テーブルを stdout へ出力する。CJK 文字・絵文字・Ambiguous 幅文字を含む場合でも列が揃うことが保証される。

#### 2.2.2 入力形式と自動検出

| 形式 | 自動検出条件 |
|------|------------|
| Markdown | 非空行の中に `\|` で始まる行が存在する |
| TSV | タブ文字を含む行が存在する（Markdown 優先） |
| CSV | 上記に該当しない場合 |

`--format` オプションで明示指定した場合は自動検出をスキップする。

**自動検出の処理順:**

```python
# parse_auto() の処理フロー
for line in lines:
    if line.strip().startswith('|'):
        return parse_md_table(lines)  # Markdown 優先

for line in lines:
    if '\t' in line:
        return parse_csv(lines, delimiter='\t')  # TSV 次優先

return parse_csv(lines, delimiter=',')  # デフォルト CSV
```

#### 2.2.3 Markdown テーブルの解析規則

- 各行の前後の空白を除去後、`|` で始まらない行はスキップ
- 空行はスキップ
- セパレータ行の判定: `stripped.strip('|')` の各文字が `- : |` のいずれかであるもの
- セルは `|` で分割後、先頭・末尾の空文字列要素を除去
- 各セルの前後の空白を除去

```python
# セパレータ行の判定例
"|---|---|"   → skip  (全文字が '-' または '|')
"|:--|--:|"   → skip  (全文字が '-', ':', '|')
"| a | b |"   → data row
```

#### 2.2.4 CSV / TSV の解析

Python 標準ライブラリの `csv.reader` を使用する。

```python
def parse_csv(lines: List[str], delimiter: str = ',') -> Optional[List[List[str]]]:
    text = ''.join(lines)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    return rows if rows else None
```

- 全セルが空の行はスキップ
- CSV の引用符（`"field with, comma"`）は `csv.reader` が処理する
- TSV の場合は `delimiter='\t'` を指定

#### 2.2.5 ボックスドローイングスタイル

| スタイル名 | 左上 | 横線 | 右上 | 縦線 | 交差 | 左中 | 右中 | 上中 | 下中 |
|-----------|------|------|------|------|------|------|------|------|------|
| `single` | `┌` | `─` | `┐` | `│` | `┼` | `├` | `┤` | `┬` | `┴` |
| `double` | `╔` | `═` | `╗` | `║` | `╬` | `╠` | `╣` | `╦` | `╩` |
| `bold` | `┏` | `━` | `┓` | `┃` | `╋` | `┣` | `┫` | `┳` | `┻` |
| `round` | `╭` | `─` | `╮` | `│` | `┼` | `├` | `┤` | `┬` | `┴` |
| `ascii` | `+` | `-` | `+` | `\|` | `+` | `+` | `+` | `+` | `+` |

各スタイルは辞書 `{'tl', 'tr', 'bl', 'br', 'h', 'v', 'lm', 'rm', 'tm', 'bm', 'cross'}` の 11 キーで定義される。

**スタイル別出力例:**

```
[single]                [double]                [bold]
┌──────┬──────┐        ╔══════╦══════╗        ┏━━━━━━┳━━━━━━┓
│ 名前 │ 得点 │        ║ 名前 ║ 得点 ║        ┃ 名前 ┃ 得点 ┃
├──────┼──────┤        ╠══════╬══════╣        ┣━━━━━━╋━━━━━━┫
│ 田中 │ 95   │        ║ 田中 ║ 95   ║        ┃ 田中 ┃ 95   ┃
└──────┴──────┘        ╚══════╩══════╝        ┗━━━━━━┻━━━━━━┛

[round]                 [ascii]
╭──────┬──────╮        +------+------+
│ 名前 │ 得点 │        | 名前 | 得点 |
├──────┼──────┤        +------+------+
│ 田中 │ 95   │        | 田中 | 95   |
╰──────┴──────╯        +------+------+
```

#### 2.2.6 ヘッダー処理

- デフォルト（`--no-header` 未指定）: 1 行目をヘッダー扱い。1 行目とデータ行の間にセパレータ行（`mid_line`）を挿入する
- `--no-header` 指定時: 全行をデータとして扱う。**全行の間に** セパレータ行を挿入する

ヘッダー行の視覚的区別はセパレータ行の挿入のみであり、ヘッダーセルに対するフォント変更等は行わない。

```python
# render_aa_table() のセパレータ挿入ロジック
for idx, row in enumerate(normalized):
    lines.append(data_row(row))
    if idx == 0 and header and len(normalized) > 1:
        lines.append(mid_line)   # ヘッダー後
    elif idx < len(normalized) - 1:
        lines.append(mid_line)   # データ行間（no-header 時）
```

#### 2.2.7 アライメント

`--align` / `-A` オプションにより列全体のテキスト配置を指定する。

| 値 | 動作 | 実装 |
|----|------|------|
| `left` | 左寄せ（デフォルト） | `text + ' ' * padding` |
| `right` | 右寄せ | `' ' * padding + text` |
| `center` | 中央寄せ | `' ' * (p//2) + text + ' ' * (p - p//2)` |

アライメントは全列に適用される。列ごとのアライメント指定は現行 v0.4.0 では非対応。

#### 2.2.8 セルパディング

`--padding` / `-p` オプションでセル内側の空白幅を指定する（デフォルト: 1）。テキストの左右それぞれに `padding` 分の空白が追加される。

水平線の幅計算: `col_widths[i] + padding * 2`

#### 2.2.9 デモモード

`--demo` フラグを指定すると以下を出力する:

1. ASCII / CJK / 全角 / 半角カナ / Ambiguous / ギリシャ文字 / カードスート / 混在 / 絵文字 を含む 10 行のデモテーブル（`--style` オプションで指定したスタイルで表示）
2. 改行 + `-- All styles demo --` ヘッダー
3. 全 5 スタイルのサンプルテーブル（小テーブル）

ファイル・フォーマットオプションは無視される。

#### 2.2.10 列数の正規化

行ごとに列数が異なる場合（不揃いの行）、`max_cols` に満たない行の末尾に空文字列を補充する。

```python
max_cols = max(len(row) for row in rows)
normalized = [row + [''] * (max_cols - len(row)) for row in rows]
```

### 2.3 mmd2ge.py

#### 2.3.1 概要

Mermaid フローチャートを Graph::Easy 入力形式に変換する。Graph::Easy は Perl の `length()` でボックス幅を計算するため CJK 文字で幅がずれる。本スクリプトは U+200B（ゼロ幅スペース）をラベルに挿入することで `length()` と表示幅を一致させる。

#### 2.3.2 対応 Mermaid 構文

| 機能 | 構文例 | 備考 |
|------|--------|------|
| 方向指定 | `graph TD`, `graph LR`, `graph RL`, `graph BT` | TD/TB は down |
| 矩形ノード | `A[label]` | |
| 角丸矩形ノード | `A(label)` | Graph::Easy では circle 扱い |
| ダイアモンドノード | `A{label}` または `A{{label}}` | shape: diamond 属性付与 |
| 円形ノード | `A((label))` | |
| 有向エッジ | `A --> B` | |
| ラベル付きエッジ（ダッシュ記法） | `A -- label --> B` | |
| ラベル付きエッジ（パイプ記法） | `A -->|label| B` | |
| 点線エッジ | `A -.-> B` | |
| 点線ラベル付き | `A -. label .-> B` | |
| 太線エッジ | `A ==> B` | |
| 太線ラベル付き | `A == label ==> B` | |
| 無向エッジ | `A --- B` | `--` に変換 |
| コメント | `%% comment` | スキップ |
| 複文 | `A --> B; B --> C` | `;` で分割 |

**非対応:** サブグラフ（`subgraph`）、classDef、click ハンドラ、style ディレクティブ、`flowchart` キーワードの第 2 引数以降

#### 2.3.3 エッジパターンの適用順

`parse_edge()` は以下の順でパターンをマッチングする（より長いパターンを先にチェックして誤マッチを防ぐ）:

1. `A -- label --> B`
2. `A -. label .-> B`
3. `A == label ==> B`
4. `A -->|label| B`
5. `A -.->\|label\| B`
6. `A ==>\|label\| B`
7. `A --> B`
8. `A -.-> B`
9. `A ==> B`
10. `A --- B`

#### 2.3.4 ノード解析

`parse_node(text, node_labels)` はノード参照文字列を解析し `(node_id, label, ge_formatted)` を返す。

- 初出時にノード形状とラベルを `node_labels[node_id]` に記録する
- 再参照時は `node_labels` から取得したラベルを使用する
- ラベルなし ID のフォールバック: ID 自体をラベルとして使用する

#### 2.3.5 出力形式

Graph::Easy 構文を stdout へ出力する。

```
# 方向が down 以外の場合のみ出力
graph { flow: right; }

# エッジ
[ 入力 ] --> [ パース ]
[ パース ] -- OK --> [ 出力 ]

# ダイアモンドノードの属性（後置）
[ 判定 ] { shape: diamond; }
```

#### 2.3.6 CJK 幅補正（ゼロ幅スペーストリック）

Graph::Easy は Perl の `length()` でボックス幅を計算するため、CJK 文字（2 カラム幅）でボーダーがずれる。

`pad_for_grapheasy(label)` は各ワイド文字（`char_display_width(ch) == 2`）の個数分だけ U+200B（ZERO WIDTH SPACE）をラベル末尾に追加する。

```python
def pad_for_grapheasy(label: str) -> str:
    extra = 0
    for ch in label:
        w = char_display_width(ch)
        if w == 2:
            extra += 1
    return label + '\u200b' * extra
```

例:

```
"入力"             → len=2, display_width=4  (不一致)
"入力\u200b\u200b" → len=4, display_width=4  (一致)
```

### 2.4 aafixwidth.py

#### 2.4.1 概要

graph-easy 等の CJK 非対応ツールが生成した ASCII Art テキストを後処理で修正する。ソースデータなしで修正できることが特徴。

#### 2.4.2 処理戦略（メインパス）

`fix_aa_widths(text)` の処理フロー:

```
1. 全行を走査
2. 水平ボーダー行（+----+----+）を検出
3. find_column_positions() で + の文字インデックス列を取得
4. ボックス構造が検出できた場合:
   - 水平ボーダー行はそのまま通過
   - コンテンツ行は fix_content_line() で補正
5. ボックス構造が検出できない場合:
   - fix_lines_simple() にフォールバック
```

#### 2.4.3 `is_horizontal_border(line)` の判定条件

以下をすべて満たす行:
- `stripped` が空でない
- 全文字が `+ - = ` のいずれか
- `+` が 2 個以上

#### 2.4.4 `fix_content_line()` の補正アルゴリズム

1. 行を `|` で分割（`parts = line.split('|')`）
2. 各セグメントの `display_width(content)` を計算
3. `surplus = display_width(content) - len(content)`（wide 文字の余剰幅）
4. セグメントが `' ' * surplus` で終わる場合: 末尾から `surplus` 文字除去
5. そうでない場合: 末尾スペースを trim し、必要なパディングを再計算

#### 2.4.5 `fix_lines_simple()` フォールバック

各行ごとに独立した補正を行う:
1. `|` が含まれない行またはボーダー行はスキップ
2. 各セグメントの末尾スペースを trim し `display_width - len` 分を除去

#### 2.4.6 `find_boxes()` について（デッドコード）

`aafixwidth.py` には完全な矩形ボックスをトレースする `find_boxes()` 関数が存在するが、現行実装では `fix_aa_widths()` から呼び出されていない。`find_column_positions()` ベースのシンプルなアプローチで十分であることが判明したため不使用となっている。将来利用を想定して保持されているが現在は到達不能コードである。

### 2.5 aacalibrate.py

#### 2.5.1 概要

ターミナルに実際にテスト文字を書き込み、カーソル位置の変化（ANSI DSR）から各文字の実レンダリング幅を計測する。計測結果を JSON プロファイルとして保存し、`aatable.py` が自動読み込みする。

#### 2.5.2 前提条件

- インタラクティブ TTY が必要（`sys.stdin.isatty()` が True であること）
- `tty` / `termios` モジュールが利用可能なこと（Linux / macOS）
- Windows ネイティブ環境では動作しない

#### 2.5.3 計測手順（1 文字分）

```
1. os.write(fd_out, b'\r\033[K')       # カーソルを行頭へ移動・行をクリア
2. os.write(fd_out, b'\033[6n')        # ANSI DSR 送信（位置照会）
3. os.read() ループで \033[row;colR を受信  → pos_before
4. os.write(fd_out, char.encode('utf-8'))  # テスト文字書き込み
5. os.write(fd_out, b'\033[6n')        # 再度位置照会
6. os.read() ループで応答受信  → pos_after
7. width = pos_after.col - pos_before.col
8. os.write(fd_out, b'\r\033[K')       # クリーンアップ
```

ターミナルはローモード（`tty.setraw()`）で操作し、`finally` ブロックで `termios.tcsetattr()` により必ず元の設定に復元される。

#### 2.5.4 プローブ文字セット

**フルプローブ（デフォルト）:**

| カテゴリ | 文字数 | 代表文字 | EAW |
|---------|-------|---------|-----|
| wide_cjk | 3 | `あ`, `漢`, `가` | W |
| fullwidth | 2 | `Ａ`, `１` | F |
| halfwidth | 1 | `ｱ` | H |
| narrow | 2 | `A`, `1` | Na |
| ambiguous | 20 | `①`, `②`, `α`, `β`, `γ`, `—`, `―`, `‐`, `♠`, `♥`, `♣`, `√`, `∞`, `≧`, `≦`, `÷`, `×`, `°`, `±`, `¥` | A |
| neutral_symbols | 2 | `♦`, `★` | N |
| emoji | 4 | `😀`, `🎉`, `🔥`, `❤` | W/A |
| emoji_zwj | 2 | `👨‍👩‍👧`, `👩‍💻` | ZWJ |
| regional_indicator | 2 | `🇯🇵`, `🇺🇸` | RI |

**クイックプローブ（`--quick`）:** ambiguous, emoji, emoji_zwj のみ

#### 2.5.5 Ambiguous 幅コンセンサス

全 Ambiguous 文字の計測値の平均が 1.5 を超える場合 → `ambiguous_width = 2`  
1.5 以下の場合 → `ambiguous_width = 1`

```python
if ambiguous_widths:
    avg = sum(ambiguous_widths) / len(ambiguous_widths)
    ambiguous_consensus = 2 if avg > 1.5 else 1
else:
    ambiguous_consensus = 1
```

#### 2.5.6 ターミナル情報の記録

以下の環境変数を `terminal` フィールドに記録する（設定への影響はなく、診断情報として保存）:

| 変数 | 型 | 例 |
|------|----|----|
| `TERM` | str | `"xterm-256color"` |
| `TERM_PROGRAM` | str | `"iTerm.app"` |
| `WT_SESSION` | bool | `true`（空文字列でない場合 true） |
| `LANG` | str | `"ja_JP.UTF-8"` |
| `LC_CTYPE` | str | `"UTF-8"` |
| `SSH_TTY` | bool | `false` |
| `WSL_DISTRO_NAME` | str | `"Ubuntu-22.04"` |

#### 2.5.7 プロファイル JSON スキーマ

```json
{
  "terminal": {
    "TERM": "<string>",
    "TERM_PROGRAM": "<string>",
    "WT_SESSION": "<bool>",
    "LANG": "<string>",
    "LC_CTYPE": "<string>",
    "SSH_TTY": "<bool>",
    "WSL_DISTRO_NAME": "<string>"
  },
  "ambiguous_width": 1,
  "probe_results": {
    "<category>": [
      {
        "char": "<string>",
        "name": "<string>",
        "codepoints": ["U+XXXX"],
        "eaw": "<string>",
        "measured_width": "<int | null>"
      }
    ]
  }
}
```

`measured_width` は計測失敗時 `null`（Python では `None`）になる。

---

## 3. データ永続化層

### 3.1 概要

AATable はステートレスな Unix フィルタ群であり、実行間で状態を保持するデータベースや永続ストアを持たない。唯一の永続データは `aacalibrate.py` が生成するターミナル幅プロファイルである。

### 3.2 `~/.aatable_profile.json`

| 項目 | 詳細 |
|------|------|
| 生成元 | `aacalibrate.py` |
| デフォルトパス | `~/.aatable_profile.json` |
| パス変更 | `aacalibrate.py -o <path>` で任意のパスに保存可能 |
| 形式 | UTF-8 JSON |
| 読み取り元 | `aatable.py`（モジュールロード時） |
| 更新タイミング | `aacalibrate.py` 実行時のみ |
| 欠損時の動作 | `FileNotFoundError` を catch し、デフォルト値 1 を使用 |
| 破損時の動作 | `json.JSONDecodeError` を catch し、デフォルト値 1 を使用 |
| フィールド欠損時 | `dict.get('ambiguous_width', 1)` でデフォルト 1 を使用 |

### 3.3 プロファイル読み込みの実装

`aatable.py` のモジュールレベルで以下が実行される:

```python
_PROFILE_PATH = os.path.expanduser('~/.aatable_profile.json')

def _load_ambiguous_width_from_profile() -> int:
    try:
        with open(_PROFILE_PATH, 'r', encoding='utf-8') as f:
            profile = json.load(f)
            return profile.get('ambiguous_width', 1)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return 1

_ambiguous_width = _load_ambiguous_width_from_profile()
```

CLI オプション `--ambiguous-width` は `main()` 内で後から上書きする:

```python
global _ambiguous_width
_ambiguous_width = args.ambiguous_width
```

### 3.4 プロファイル書き込みの実装

`aacalibrate.py` は `--json` フラグなしの場合にファイルへ書き込む:

```python
profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
with open(args.output, 'w', encoding='utf-8') as f:
    f.write(profile_json)
```

`ensure_ascii=False` により日本語文字がエスケープされずに保存される。

---

## 4. ステートマシン

### 4.1 概要

AATable のスクリプトはいずれも単一パスのテキスト処理パイプラインであり、明示的なステートマシン（FSM/HSM）を持たない。各スクリプトは「入力を読む → 変換する → 出力する」という線形フローのみである。

### 4.2 Markdown パーサの暗黙的状態

`parse_md_table()` は各行を独立して処理するシンプルなループである。前後の行の状態を保持しない。

```
各行 → セパレータ行か？ → スキップ
      → 空行か？       → スキップ
      → | で始まるか？ → セルを抽出してリストに追加
      → 上記以外       → スキップ
```

### 4.3 Mermaid パーサの暗黙的状態

`parse_mermaid()` は以下の可変コンテキストを持つが、FSM の「状態」ではない:

- `direction`: 方向宣言（最後に見つかった値で上書き）
- `node_labels`: ノード ID → (label, shape) の辞書（行を読み進めるにつれて更新）

```
各行 → graph 宣言か？    → direction を更新
      → ステートメント分割（; 区切り）
          → エッジか？ → Graph::Easy 行を追加
          → ノード定義か？ → Graph::Easy 行を追加
          → それ以外  → スキップ
```

### 4.4 ターミナル計測における状態変化

`aacalibrate.py` はターミナルを raw モードへ切り替えるという副作用を持つ。これは FSM 的な「状態」だが、`finally` ブロックで必ず復元されるため、観測可能な状態変化は一時的である。

```
[通常モード]
    │ tty.setraw()
    ▼
[raw モード] ← 計測ループ（各文字に対して独立）
    │ termios.tcsetattr()（finally）
    ▼
[通常モード]
```

### 4.5 aafixwidth.py の処理分岐

`fix_aa_widths()` はボックス構造の検出結果によって 2 種の処理パスに分岐する:

```
入力テキスト
    │
    ▼
find_column_positions() でボックス構造を検出
    │
    ├── 検出できた → fix_content_line() でカラム位置ベースの補正
    │
    └── 検出できない → fix_lines_simple() で行単位の補正
    │
    ▼
修正済みテキスト出力
```

---

## 5. ビジネスロジック

### 5.1 `display_width(text: str) -> int`

CJK・絵文字対応の「表示幅」計算関数。Python の `len()` に代わる核心的ロジック。`aatable.py` に正規実装があり、`aafixwidth.py` と `mmd2ge.py` に簡略版が存在する。

**アルゴリズム（aatable.py 版）:**

```
display_width(text)
  → split_grapheme_clusters(text)  # 視覚的単位に分割
  → grapheme_width(cluster)        # 各クラスターの幅を計算
  → sum(widths)                    # 合計
```

**文字種別の期待動作:**

| 文字 | `len()` | `display_width()` | 理由 |
|------|---------|-------------------|------|
| `A` | 1 | 1 | ASCII Narrow |
| `あ` | 1 | 2 | Wide (W) |
| `漢字` | 2 | 4 | Wide × 2 |
| `Ａ` | 1 | 2 | Fullwidth (F) |
| `ｱ` | 1 | 1 | Halfwidth (H) |
| `①` | 1 | 1 or 2 | Ambiguous (A) |
| `😀` | 2 | 2 | Wide emoji |
| `👨‍👩‍👧` | 7 | 2 | ZWJ sequence → 1 glyph |
| `🇯🇵` | 2 | 2 | Regional indicator pair |
| `👋🏽` | 2 | 2 | Emoji + skin modifier |
| `☺️` | 2 | 2 | Emoji + variation selector |
| `Hello世界!` | 9 | 11 | 混在 |

### 5.2 `split_grapheme_clusters(text: str) -> List[str]`

UAX#29 の完全実装ではなく、実用上問題となるケースを手動で処理する近似実装（`aatable.py` のみ）。

**処理順序（i = 現在位置）:**

```
1. 地域指標ペアの検出:
   - codepoints[i] が地域指標（U+1F1E6〜U+1F1FF）かつ
   - codepoints[i+1] も地域指標
   → 2 コードポイントを 1 クラスターとする

2. 絵文字ベースシーケンスの検出:
   - codepoints[i] が _is_emoji_base() に該当
   → 後続の ZWJ+次文字 / VS15 / VS16 / Emoji Modifier /
     結合文字（Mn, Me）をクラスターに吸収
   
3. 通常文字 + 結合文字の検出:
   - 後続の Mn/Me カテゴリ文字および VS15/VS16 をクラスターに吸収
```

**`_is_emoji_base()` が対象とするコードポイント範囲:**

| 範囲 | 説明 |
|------|------|
| U+1F600〜U+1F64F | 顔文字 |
| U+1F900〜U+1F9FF | 補助記号 |
| U+1FA00〜U+1FA6F | チェス記号 |
| U+1FA70〜U+1FAFF | 記号拡張A |
| U+2600〜U+27BF | その他記号・装飾 |
| U+1F300〜U+1F5FF | その他記号・絵文字 |
| U+1F680〜U+1F6FF | 輸送・地図 |
| U+1F1E0〜U+1F1FF | 地域指標 |
| 個別 | U+2640, U+2642, U+2695, U+2696, U+2708, U+2764（ZWJ の一般的なジョイナー） |

### 5.3 `grapheme_width(cluster: str) -> int`

クラスター → 表示幅（カラム数）の変換。適用順:

1. **ZWJ シーケンス**: クラスターに U+200D (ZWJ) が含まれる → **2**
2. **国旗ペア**: 先頭コードポイントが地域指標（U+1F1E6〜U+1F1FF）→ **2**
3. **絵文字ベース**: 先頭コードポイントが `_is_emoji_base()` に該当 → **2**
4. **EAW ルックアップ**: `unicodedata.east_asian_width(cluster[0])` で判定
   - `'W'` または `'F'` → **2**
   - `'A'` (Ambiguous) → **`_ambiguous_width`**（1 または 2）
   - `'Na'`, `'H'`, `'N'` → **1**

### 5.4 `pad_to_width(text: str, target_width: int, align: str = 'left') -> str`

`display_width(text)` が `target_width` と等しくなるまで ASCII 空白（U+0020）でパディングする関数。

```python
current = display_width(text)
padding = max(0, target_width - current)

if align == 'right':
    return ' ' * padding + text
elif align == 'center':
    left = padding // 2
    right = padding - left
    return ' ' * left + text + ' ' * right
else:  # left
    return text + ' ' * padding
```

**動作例:**

```python
pad_to_width("田中", 8)              # "田中    "  (4 + 4 空白)
pad_to_width("Alice", 8)             # "Alice   "  (5 + 3 空白)
pad_to_width("田中", 8, "right")     # "    田中"  (4 空白 + 4)
pad_to_width("田中", 8, "center")    # "  田中  "  (2 + 4 + 2)
pad_to_width("A", 1)                 # "A"         (パディング不要)
pad_to_width("AB", 1)                # "AB"        (target < current → padding=0)
```

### 5.5 `render_aa_table(rows, style_name, padding, header, align) -> str`

テーブルレンダリングの中心関数。

**処理フロー:**

```
1. 列数正規化: max_cols を計算、短い行に '' を補充
2. 列幅計算: col_widths[i] = max(display_width(cell)) across all rows for column i
3. 水平線生成:
   top_line: tl + (h * (col_w + pad*2)) + tm + ... + tr
   mid_line: lm + (h * (col_w + pad*2)) + cross + ... + rm
   bot_line: bl + (h * (col_w + pad*2)) + bm + ... + br
4. データ行生成:
   v + (' ' * pad) + pad_to_width(cell, col_w, align) + (' ' * pad) + v + ...
5. 組み立て:
   top → data[0] → (header: mid) → data[1] → mid → data[2] → mid → ... → bot
```

**水平線ビルダー `h_line(left, mid, right, fill)`:**

```python
def h_line(left: str, mid: str, right: str, fill: str) -> str:
    segments = [fill * (col_widths[i] + padding * 2) for i in range(max_cols)]
    return left + mid.join(segments) + right
```

### 5.6 `fix_aa_widths(text: str) -> str`（aafixwidth.py）

CJK 幅ずれの修正ロジック。

**`find_column_positions(lines)` の処理:**

```python
for line in lines:
    if is_horizontal_border(line):
        positions = [i for i, ch in enumerate(line) if ch == '+']
        if len(positions) >= 2:
            return positions
return []
```

**`fix_content_line(line, column_positions)` の処理:**

```python
parts = line.split('|')
for i in range(1, len(parts) - 1):
    content = parts[i]
    content_display = display_width(content)
    content_len = len(content)
    width_diff = content_display - content_len  # wide 文字による余剰

    if width_diff > 0 and content.endswith(' ' * width_diff):
        result += content[:-width_diff]  # 末尾から surplus 分除去
    elif width_diff > 0:
        trimmed = content.rstrip(' ')
        needed_padding = max(0, expected_chars - display_width(trimmed) - width_diff)
        result += trimmed + ' ' * needed_padding
    else:
        result += content
```

### 5.7 `pad_for_grapheasy(label: str) -> str`（mmd2ge.py）

```python
def pad_for_grapheasy(label: str) -> str:
    extra = 0
    for ch in label:
        w = char_display_width(ch)
        if w == 2:
            extra += 1
    return label + '\u200b' * extra
```

**動作保証:**  
`len(pad_for_grapheasy(label)) == display_width(label)` が成立する。ただし `display_width` はコードポイント単位の簡略実装（`mmd2ge.py` 内の `char_display_width()` の合計）を使用する。

---

## 6. API / 外部境界

### 6.1 CLI コマンド詳細

#### 6.1.1 `aatable.py`

```
python3 aatable.py [OPTIONS] [FILE]
```

| オプション | 短縮形 | 型 | デフォルト | 説明 |
|-----------|--------|----|-----------|----|
| `--format` | `-f` | `auto\|md\|csv\|tsv` | `auto` | 入力形式。`auto` は内容から自動検出（Markdown → TSV → CSV の優先順位） |
| `--style` | `-s` | `single\|double\|bold\|round\|ascii` | `single` | ボックス描画スタイル |
| `--padding` | `-p` | int | `1` | セル内側の空白幅（両側） |
| `--no-header` | — | flag | off | 1 行目をヘッダーとして扱わない |
| `--ambiguous-width` | `-a` | `1\|2` | `1` | Ambiguous 文字の幅（プロファイルよりも優先） |
| `--align` | `-A` | `left\|right\|center` | `left` | セルテキスト配置 |
| `--demo` | — | flag | off | デモテーブルと全スタイルを表示。ファイル・フォーマットオプションを無視 |

**終了コード:**

| コード | 意味 |
|--------|------|
| 0 | 正常終了 |
| 1 | 有効な表形式データが見つからない（`parse_auto()` が `None` を返した場合） |

**stdin からの読み込み時の TTY 検出:**

```python
if sys.stdin.isatty():
    print('Paste Markdown table (Ctrl+D to finish):', file=sys.stderr)
input_lines = sys.stdin.readlines()
```

#### 6.1.2 `mmd2ge.py`

```
python3 mmd2ge.py [FILE]
```

| 引数 | 説明 |
|------|------|
| `FILE` | Mermaid ファイルパス。省略時またはハイフン（`-`）指定時は stdin を読む |

`argparse` を使用せず `sys.argv` から直接取得。`len(sys.argv) > 1 and sys.argv[1] != '-'` で判定。

**出力:** Graph::Easy 構文（stdout）。`graph-easy --as=boxart` へのパイプを想定。

#### 6.1.3 `aafixwidth.py`

```
python3 aafixwidth.py [OPTIONS] [FILE]
```

| オプション | 短縮形 | 型 | デフォルト | 説明 |
|-----------|--------|----|-----------|----|
| `--ambiguous-width` | `-a` | `1\|2` | `1` | Ambiguous 文字の幅 |

**終了コード:** 常に 0（エラー処理なし・入力をそのまま出力する）

**出力:** `print(fix_aa_widths(text), end='')` により末尾の改行を制御

#### 6.1.4 `aacalibrate.py`

```
python3 aacalibrate.py [OPTIONS]
```

| オプション | 短縮形 | 型 | デフォルト | 説明 |
|-----------|--------|----|-----------|----|
| `--output` | `-o` | path | `~/.aatable_profile.json` | プロファイル出力先 |
| `--quick` | `-q` | flag | off | クイックモード（Ambiguous + 絵文字のみ） |
| `--json` | — | flag | off | プロファイル JSON を stdout へ出力（ファイル書き込みなし） |
| `--quiet` | — | flag | off | 進行状況を stderr へ出力しない |

**制約:** インタラクティブ TTY が必要（`sys.stdin.isatty() == False` の場合はエラーメッセージを stderr に出力して `sys.exit(1)`）。

### 6.2 外部ツール連携

| ツール | 連携形態 | 必須かどうか |
|--------|---------|------------|
| `graph-easy` | パイプ受信側 | `mmd2ge.py` 使用時のみ必要 |
| `psql`, `mysql` 等 | パイプ送信側（CSV 出力） | 任意 |
| `docker ps` | パイプ送信側（TSV 出力） | 任意 |
| `git log` | パイプ送信側（CSV 出力） | 任意 |
| `jq` | パイプ中間処理 | 任意 |

### 6.3 データフロー図

```
表形式データパイプライン:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ psql --csv   │ ──> │  aatable.py  │ ──> │    stdout    │
│ git log --   │     └──────────────┘     └──────────────┘
│ docker ps    │           ↑
└──────────────┘    ~/.aatable_profile.json
                          ↑
                  ┌───────────────────┐
                  │  aacalibrate.py   │
                  └───────────────────┘

Mermaid フローチャートパイプライン:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ flow.mmd     │ ──> │  mmd2ge.py   │ ──> │  graph-easy  │ ──> │ aafixwidth   │ ──> │    stdout    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### 6.4 エラー境界

| スクリプト | エラー条件 | 対応 |
|-----------|----------|------|
| `aatable.py` | 有効な表形式データなし | stderr にエラーメッセージ + exit(1) |
| `aatable.py` | ファイルが存在しない | Python 標準の FileNotFoundError（未 catch、スタックトレース表示） |
| `aacalibrate.py` | 非インタラクティブ TTY | stderr にエラーメッセージ + exit(1) |
| `aacalibrate.py` | カーソル位置取得失敗 | `measured_width = None` として処理を継続 |
| `aafixwidth.py` | 任意の入力 | エラーなし（ボックス構造なし → simple フォールバック） |
| `mmd2ge.py` | 未知の Mermaid 構文 | スキップして無視 |

---

## 7. UI

### 7.1 概要

AATable はすべてコマンドラインインターフェースであり、GUI・Web UI・TUI を持たない。ユーザーインターフェースはターミナルテキスト出力のみである。

### 7.2 stdout / stderr の分離

| 出力先 | 内容 |
|--------|------|
| stdout | 整形済みテーブル（`aatable.py`, `aafixwidth.py`）、Graph::Easy 構文（`mmd2ge.py`）、`--json` 指定時のプロファイル JSON（`aacalibrate.py`） |
| stderr | エラーメッセージ、プログレス表示、インタラクティブプロンプト、プロファイルサマリー（`aacalibrate.py`） |

この分離により、`aatable.py` の出力はパイプ先のツールに渡しても stderr のメッセージが混入しない。

### 7.3 インタラクティブプロンプト

stdin が TTY の場合、各スクリプトは使用方法をガイドするプロンプトを stderr へ表示する:

**`aatable.py`:**
```
Paste Markdown table (Ctrl+D to finish):
```

**`mmd2ge.py`:**
```
Paste Mermaid flowchart (Ctrl+D to finish):
```

stdin がパイプの場合は表示しない（`sys.stdin.isatty()` で判定）。

### 7.4 `aacalibrate.py` の出力

**stderr（通常モード）:**
```
Probing terminal character widths...

  あ  width=2  (Hiragana A, EAW=W) OK
  漢  width=2  (Kanji, EAW=W) OK
  ...

=== AATable Terminal Profile ===
Terminal: iTerm.app
Ambiguous width: 2

[wide_cjk]
  あ  → 2 columns  (Hiragana A)
  ...
```

**stdout（`--json` 指定時）:**
```json
{
  "terminal": { ... },
  "ambiguous_width": 2,
  "probe_results": { ... }
}
```

`--quiet` フラグで stderr の出力を抑制できる。`--json --quiet` を組み合わせると stdout にのみ JSON が出力され、他のツールへのパイプが可能になる。

---

## 8. 設定

### 8.1 プロファイル自動読み込み

`aatable.py` はモジュールロード時に `~/.aatable_profile.json` を読み込む。

```python
_PROFILE_PATH = os.path.expanduser('~/.aatable_profile.json')
_ambiguous_width = _load_ambiguous_width_from_profile()
```

| 状況 | 動作 |
|------|------|
| ファイルが存在し有効な JSON | `ambiguous_width` フィールドを読み込む |
| ファイルが存在しない | `FileNotFoundError` を catch → デフォルト値 1 |
| JSON が壊れている | `json.JSONDecodeError` を catch → デフォルト値 1 |
| フィールドが存在しない | `dict.get('ambiguous_width', 1)` → デフォルト 1 |

### 8.2 `--ambiguous-width` オプションとプロファイルの優先順位

優先順位（高い順）: CLI オプション > プロファイル > ハードコードデフォルト（1）

ただし v0.4.0 では以下の問題がある:

**既知の問題:** `argparse` の `--ambiguous-width` デフォルト値が `1` に設定されているため、CLI オプション未指定時でも `args.ambiguous_width == 1` となり、`global _ambiguous_width = args.ambiguous_width` でプロファイルの値が上書きされる。

```python
# 現行実装（v0.4.0）の問題
parser.add_argument('--ambiguous-width', default=1, ...)
# ...
_ambiguous_width = args.ambiguous_width  # 常に 1 で上書きされる

# 正しい実装（将来の改善案）
parser.add_argument('--ambiguous-width', default=None, ...)
# ...
if args.ambiguous_width is not None:
    _ambiguous_width = args.ambiguous_width
```

現在の回避策: `aacalibrate.py` でプロファイルを生成しても `aatable.py` では `--ambiguous-width 2` を明示指定する必要がある（macOS ユーザーの場合）。

### 8.3 `_ambiguous_width` グローバル変数パターン

全 4 スクリプトで同様のグローバル変数パターンを採用している:

```python
_ambiguous_width = 1  # モジュールレベル（aafixwidth.py, mmd2ge.py はここで宣言）

def main():
    # ...
    global _ambiguous_width
    _ambiguous_width = args.ambiguous_width
```

`aatable.py` のみプロファイル読み込みも行う。`aafixwidth.py` と `mmd2ge.py` はプロファイル読み込みなし（常に CLI オプションかデフォルト値）。

### 8.4 ターミナル環境変数（診断情報）

`aacalibrate.py` は以下の環境変数を `terminal` フィールドに記録する。これらは `ambiguous_width` の自動判定には使用されない（すべて実測値から判定する）。診断・デバッグ目的でのみ保存される。

| 変数 | 用途 |
|------|------|
| `TERM` | ターミナル識別子（例: `xterm-256color`, `screen-256color`） |
| `TERM_PROGRAM` | ターミナルアプリ名（例: `iTerm.app`, `Apple_Terminal`, `tmux`） |
| `WT_SESSION` | Windows Terminal かどうか（空文字列でない場合 `True`） |
| `LANG` | ロケール（例: `ja_JP.UTF-8`） |
| `LC_CTYPE` | 文字種別ロケール |
| `SSH_TTY` | SSH 接続かどうか（空文字列でない場合 `True`） |
| `WSL_DISTRO_NAME` | WSL ディストリビューション名（例: `Ubuntu-22.04`） |

### 8.5 プロファイルパスのカスタマイズ

`aacalibrate.py` は `--output` / `-o` オプションで任意のパスにプロファイルを保存できる。ただし `aatable.py` は常に `~/.aatable_profile.json` のみを読み込む（カスタムパスの自動読み込みは未対応）。

---

## 9. 依存関係

### 9.1 実行環境

| 要件 | 詳細 |
|------|------|
| Python | 3.9 以上推奨（Python 3.8 は 2024 年 10 月 EOL のため非推奨。動作はするが保証外） |
| 外部 Python パッケージ | なし（pip install 不要） |
| OS | Linux / macOS / Windows（WSL 経由） |

**OS 別制約:**

| OS | aatable.py | aafixwidth.py | mmd2ge.py | aacalibrate.py |
|----|-----------|--------------|-----------|---------------|
| Linux | 動作 | 動作 | 動作 | 動作 |
| macOS | 動作 | 動作 | 動作 | 動作 |
| Windows (WSL) | 動作 | 動作 | 動作 | 動作 |
| Windows ネイティブ | 動作 | 動作 | 動作 | **非対応**（`tty`/`termios` なし） |

### 9.2 標準ライブラリの使用

| モジュール | 使用スクリプト | 用途 |
|-----------|--------------|------|
| `sys` | 全スクリプト | stdin/stdout/stderr, sys.argv, sys.exit |
| `os` | aatable.py, aacalibrate.py | `os.path.expanduser`, `os.read`, `os.write` |
| `unicodedata` | 全スクリプト | `east_asian_width()`, `category()` |
| `argparse` | aatable.py, aafixwidth.py, aacalibrate.py | CLI オプション解析 |
| `json` | aatable.py, aacalibrate.py | プロファイルの読み書き |
| `csv` | aatable.py | CSV / TSV の解析 |
| `io` | aatable.py | `io.StringIO` を使った CSV パース |
| `re` | aafixwidth.py, mmd2ge.py, aacalibrate.py | 正規表現 |
| `typing` | aatable.py, aafixwidth.py, mmd2ge.py | 型アノテーション（`List`, `Optional`, `Tuple`, `Dict`） |
| `tty` | aacalibrate.py | ターミナルをローモードに設定 |
| `termios` | aacalibrate.py | ターミナル設定の保存・復元 |

### 9.3 オプションの外部依存

| ツール | 用途 | 必須かどうか |
|--------|------|------------|
| `graph-easy` (CPAN) | `mmd2ge.py` の出力を ASCII Art フローチャートに変換 | `mmd2ge.py` 使用時のみ必要 |

**`graph-easy` のインストール:**

```bash
# cpanminus を使う場合
cpanm Graph::Easy

# cpanminus がない場合
perl -MCPAN -e 'install Graph::Easy'

# cpanminus 自体をインストールする場合
curl -L https://cpanmin.us | perl - Graph::Easy
```

### 9.4 Python バージョンとの互換性

| 機能 | 最低バージョン |
|------|-------------|
| `unicodedata.east_asian_width()` | Python 2.7+ |
| `from typing import List, Optional` | Python 3.5+ |
| `f-string` | Python 3.6+ |
| `os.path.expanduser()` | 全バージョン |
| `unicodedata.category()` | 全バージョン |

f-string の使用（例: `f'[ {padded} ]'`）が Python 3.6 以上を必要とするため、3.5 以前では動作しない。

---

## 10. 非機能要件

### 10.1 CJK 全角対応

すべての Wide (W) および Fullwidth (F) 文字は表示幅 2 として処理される。

**EAW カテゴリと幅の対応:**

| EAW | 名称 | 幅 | 代表例 |
|-----|------|----|--------|
| W | Wide | 2 | CJK 統合漢字、拡張ブロック、ひらがな、カタカナ（全角）、ハングル |
| F | Fullwidth | 2 | `Ａ`〜`Ｚ`, `ａ`〜`ｚ`, `０`〜`９`, `！`, `？` 等 |
| Na | Narrow | 1 | ASCII 文字全般 |
| H | Halfwidth | 1 | 半角カタカナ `ｱ`〜`ﾝ`、半角記号 |
| A | Ambiguous | 1 or 2 | ターミナル依存（後述） |
| N | Neutral | 1 | 多くの記号・制御文字 |

判定ロジック:

```python
eaw = unicodedata.east_asian_width(ch)
if eaw in ('W', 'F'):
    return 2
if eaw == 'A':
    return _ambiguous_width  # 1 or 2
return 1
```

### 10.2 Ambiguous Width 対応

Unicode TR11（East Asian Width）の Ambiguous カテゴリ文字は「ターミナル依存」と定義されている。異なるターミナルで以下のような差異が生じる:

| ターミナル | Ambiguous 幅 | 影響する文字例 |
|-----------|------------|--------------|
| Windows Terminal | 1 | `①②③`, `αβγ`, `♠♥♦♣`, `—`, `±`, `×`, `÷`, `°`, `¥` 等 |
| VS Code 統合ターミナル | 1 | 同上 |
| macOS Terminal.app | 2 | 同上 |
| iTerm2（CJK ロケール） | 2 | 同上 |

**推奨ワークフロー:**

1. 初回: `python3 aacalibrate.py --quick` でプロファイルを生成
2. 以降: `aatable.py` が自動的に正しい幅を使用（v0.4.0 では CLI オプション問題のため `--ambiguous-width 2` を明示指定が確実）

### 10.3 絵文字・グラフェームクラスター対応

| 種別 | 例 | `len()` | `display_width()` | 処理方法 |
|-----|----|---------|--------------------|---------|
| 単一絵文字 | `😀` | 2（サロゲートペア） | 2 | EAW = W |
| ZWJ シーケンス | `👨‍👩‍👧` | 7 | 2 | ZWJ 検出 → 1 クラスター |
| 国旗ペア | `🇯🇵` | 2 | 2 | 地域指標ペア検出 |
| スキントーン修飾 | `👋🏽` | 2 | 2 | Emoji Modifier 吸収 |
| 異体字セレクタ付き | `☺️` | 2 | 2 | VS16 吸収 |
| テキスト異体字 | `☺︎` | 2 | 1 | VS15 → テキスト扱い |

`aatable.py` はグラフェームクラスター分割を実装しているが、`aafixwidth.py` と `mmd2ge.py` はコードポイント単位の簡略実装を使用しているため、ZWJ シーケンス等の精度がやや低い。

### 10.4 パフォーマンス特性

標準ライブラリのみ・最適化なしのため、大規模データセットでのパフォーマンスは保証されない。

| 処理 | 計算量 | 備考 |
|------|--------|------|
| `split_grapheme_clusters()` | O(n) | n = テキストのコードポイント数 |
| `display_width()` | O(n) | n = テキストのコードポイント数 |
| `render_aa_table()` | O(R × C) | R = 行数, C = 列数 |
| `parse_md_table()` | O(n) | n = 行数 |

実用規模（数千行以下のテーブル）では問題なし。

### 10.5 文字コード

全ファイル IO は UTF-8 エンコーディングで処理する。

```python
open(path, 'r', encoding='utf-8')
open(path, 'w', encoding='utf-8')
```

stdin の読み込みはエンコーディング指定なし（Python のデフォルトロケール依存）。UTF-8 ロケール環境を前提とする。

### 10.6 セキュリティ

| 項目 | 状態 |
|------|------|
| ファイルシステムアクセス | `~/.aatable_profile.json` の読み書きのみ |
| ネットワーク通信 | なし |
| コード実行（eval 等） | なし |
| 外部プロセス呼び出し | なし（`graph-easy` はパイプで外部に委ねる） |
| 入力サニタイズ | 不要（テキスト変換のみ） |

### 10.7 後方互換性

| 項目 | 状態 |
|------|------|
| semver 適用 | 未適用 |
| PyPI 配布 | 未対応 |
| CLI インターフェース保証 | なし（スクリプト直接コピー利用のため） |
| プロファイル形式保証 | 後続バージョンで変更の可能性あり |

---

## 11. テスト戦略

### 11.1 現状の確認

リポジトリに自動テストコード（`tests/` ディレクトリ、`pytest`、`unittest` 等）は一切存在しない。CI/CD 設定（GitHub Actions 等）も存在しない。

### 11.2 `--demo` による動作確認

`aatable.py --demo` コマンドが実質的な統合テスト手段として機能している。以下の文字種を含む 10 行のデモテーブルを全 5 スタイルで出力する:

| 行 | 文字種 | 確認内容 |
|----|--------|---------|
| ASCII `Hello` | Narrow | 基本動作 |
| 全角 `こんにちは` | Wide (W) | 全角 5 文字 = 幅 10 |
| 全角英数 `Ａ１` | Fullwidth (F) | 全角英数 2 文字 = 幅 4 |
| 半角カナ `ｱｲｳ` | Halfwidth (H) | 半角カナ 3 文字 = 幅 3 |
| Ambiguous `①②③` | Ambiguous (A) | デフォルト幅 1 × 3 = 幅 3（または 6） |
| Greek `α β γ` | Ambiguous (A) | スペース含む 5 文字 = 幅 7 |
| Card suits `♠♥♦♣` | Ambiguous (A) | 記号 4 文字 |
| 混在 `Hello世界!` | 混在 | ASCII 7 + CJK 4 = 幅 11 |
| 絵文字 `😀🎉` | Emoji | 絵文字 2 文字 = 幅 4 |

### 11.3 推奨ユニットテスト

#### 11.3.1 `display_width()` テスト

```python
# 基本
assert display_width("") == 0
assert display_width("Hello") == 5
assert display_width("漢字") == 4
assert display_width("Ａ１") == 4
assert display_width("ｱｲｳ") == 3

# 絵文字
assert display_width("😀") == 2
assert display_width("👨\u200d👩\u200d👧") == 2   # ZWJ sequence
assert display_width("🇯🇵") == 2                   # regional indicator pair
assert display_width("👋🏽") == 2                   # skin tone modifier

# 混在
assert display_width("Hello世界!") == 11
assert display_width("田中太郎") == 8

# Ambiguous（_ambiguous_width = 1 時）
import aatable
aatable._ambiguous_width = 1
assert aatable.display_width("①②③") == 3
aatable._ambiguous_width = 2
assert aatable.display_width("①②③") == 6
```

#### 11.3.2 `split_grapheme_clusters()` テスト

```python
assert split_grapheme_clusters("AB") == ["A", "B"]
assert split_grapheme_clusters("あ漢") == ["あ", "漢"]
assert len(split_grapheme_clusters("👨\u200d👩\u200d👧")) == 1   # ZWJ → 1 cluster
assert len(split_grapheme_clusters("🇯🇵")) == 1                  # flag → 1 cluster
assert len(split_grapheme_clusters("👋🏽")) == 1                  # modifier → 1 cluster
```

#### 11.3.3 `pad_to_width()` テスト

```python
assert pad_to_width("田中", 8) == "田中    "
assert pad_to_width("Alice", 8) == "Alice   "
assert pad_to_width("田中", 8, "right") == "    田中"
assert pad_to_width("abc", 6, "center") == " abc  "
assert pad_to_width("ab", 1) == "ab"    # padding=0 when text > target
```

#### 11.3.4 `parse_md_table()` テスト

```python
# 基本
lines = ["| a | b |", "|---|---|", "| 1 | 2 |"]
assert parse_md_table(lines) == [["a", "b"], ["1", "2"]]

# セパレータのみ
assert parse_md_table(["|---|---|"]) is None or parse_md_table(["|---|---|"]) == []

# 空入力
assert parse_md_table([]) is None

# コロン整列記法
lines = ["| h |", "|:---:|", "| v |"]
assert parse_md_table(lines) == [["h"], ["v"]]
```

#### 11.3.5 `render_aa_table()` テスト

```python
rows = [["name", "val"], ["田中", "1"]]
result = render_aa_table(rows)
# 幅チェック: 全行の長さが一致すること
lines = result.split('\n')
widths = [display_width(line) for line in lines if line]
assert len(set(widths)) == 1  # 全行同幅

# スタイル別境界文字の確認
for style in ('single', 'double', 'bold', 'round', 'ascii'):
    r = render_aa_table(rows, style_name=style)
    assert len(r) > 0
```

#### 11.3.6 `parse_mermaid()` テスト

```python
# 基本エッジ
lines = ["graph TD", "A[Start] --> B[End]"]
direction, ge_lines, _ = parse_mermaid(lines)
assert direction == "down"
assert "[ Start ]" in ge_lines[0]
assert "-->" in ge_lines[0]

# ラベル付きエッジ
lines = ["graph LR", "A --> B", "B -- label --> C"]
direction, ge_lines, _ = parse_mermaid(lines)
assert direction == "right"
assert any("label" in l for l in ge_lines)

# CJK ラベル
lines = ["A[入力] --> B[出力]"]
_, ge_lines, _ = parse_mermaid(lines)
assert "\u200b" in ge_lines[0]  # U+200B が挿入されている
```

#### 11.3.7 `fix_aa_widths()` テスト

```python
# 崩れた ASCII Art を修正する
broken = "+------+\n| 田中 |\n+------+"
fixed = fix_aa_widths(broken)
lines = fixed.split('\n')
# 各行の表示幅が一致すること
assert display_width(lines[0]) == display_width(lines[1]) == display_width(lines[2])
```

### 11.4 プロパティベーステスト（推奨）

`pad_to_width()` および `render_aa_table()` に対して、以下の不変条件をプロパティベーステスト（hypothesis 等）で検証する:

1. `display_width(pad_to_width(text, target, align)) == target`（`target >= display_width(text)` の場合）
2. `render_aa_table(rows)` の全行の `display_width` が等しい
3. `pad_for_grapheasy(label)` で `len(result) == display_width(result)`

### 11.5 CI / CD 推奨設定

```yaml
# .github/workflows/test.yml （推奨）
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: python3 -m pytest tests/ -v
      - run: python3 aatable.py --demo  # スモークテスト
```

### 11.6 手動テストシナリオ

| シナリオ | コマンド | 期待結果 |
|---------|---------|---------|
| デモ動作確認 | `python3 aatable.py --demo` | 崩れのないテーブル表示 |
| CJK 列幅 | `echo "| 名前 | 得点 |↵|---|---|↵| 田中太郎 | 95 |" \| python3 aatable.py` | 全行同幅 |
| 全スタイル | `python3 aatable.py --demo --style double` | double スタイルのデモ |
| 右寄せ | `echo "..." \| python3 aatable.py --align right` | 数値が右寄せ |
| Ambiguous 幅 1 | `python3 aatable.py -a 1 ...` | ① が 1 幅 |
| Ambiguous 幅 2 | `python3 aatable.py -a 2 ...` | ① が 2 幅 |
| CSV 入力 | `python3 aatable.py -f csv data.csv` | CSV が正しくパース |
| TSV 入力 | `python3 aatable.py -f tsv data.tsv` | TSV が正しくパース |
| Mermaid 変換 | `echo "graph TD↵A --> B" \| python3 mmd2ge.py` | GE 形式出力 |

---

## 12. デプロイ / 運用

### 12.1 現状の配布方法

PyPI 未登録。pip install は非対応。

配布・使用方法は以下の 2 通りのみ:

**方法 1: git clone して直接実行**

```bash
git clone https://github.com/opaopa6969/AATable.git
cd AATable
chmod +x aatable.py aafixwidth.py mmd2ge.py aacalibrate.py
python3 aatable.py --demo
```

**方法 2: スクリプトをコピーして PATH に配置**

```bash
mkdir -p ~/bin
cp /path/to/AATable/aatable.py ~/bin/aatable
cp /path/to/AATable/aafixwidth.py ~/bin/aafixwidth
cp /path/to/AATable/mmd2ge.py ~/bin/mmd2ge
cp /path/to/AATable/aacalibrate.py ~/bin/aacalibrate
chmod +x ~/bin/aatable ~/bin/aafixwidth ~/bin/mmd2ge ~/bin/aacalibrate
```

`~/bin` が `PATH` に含まれていない場合:

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 12.2 インストール手順（詳細）

#### Python バージョン確認

```bash
python3 --version
# 3.9.x 以上を推奨
```

#### Graph::Easy のインストール（mmd2ge.py 使用時）

```bash
# macOS（Homebrew Perl）
brew install cpanminus
cpanm Graph::Easy

# Ubuntu / Debian
sudo apt install cpanminus
cpanm Graph::Easy

# RHEL / CentOS
sudo yum install perl-CPAN
perl -MCPAN -e 'install Graph::Easy'
```

#### 動作確認

```bash
python3 aatable.py --demo
```

以下のような整列されたテーブルが表示されれば成功:

```
┌───────────┬────────────┬────┬────────────────────────────┐
│ 種類      │ 文字       │ 幅 │ 説明                       │
├───────────┼────────────┼────┼────────────────────────────┤
│ ASCII     │ Hello      │ 5  │ Half-width                 │
├───────────┼────────────┼────┼────────────────────────────┤
│ 全角      │ こんにちは │ 10 │ Wide (W)                   │
...
```

### 12.3 Ambiguous 幅の初期設定

初回インストール後、ターミナルの Ambiguous 幅を自動検出するためにキャリブレーションを実行することを推奨する:

```bash
# 高速プローブ（約 20 秒）
python3 aacalibrate.py --quick

# フルプローブ（約 60 秒）
python3 aacalibrate.py
```

実行後、`~/.aatable_profile.json` が生成される。v0.4.0 の既知問題のため、macOS ユーザーは `--ambiguous-width 2` の明示指定も必要。

### 12.4 アップグレード

バージョン管理は git のみ。アップグレード方法:

```bash
cd /path/to/AATable
git pull origin master
```

スクリプトをコピーして使用している場合は、アップグレード後に再度コピーが必要:

```bash
cp /path/to/AATable/aatable.py ~/bin/aatable
```

### 12.5 PyPI 配布の将来計画

現時点（v0.4.0）では PyPI への登録計画はない。配布する場合の対応事項:

| 課題 | 対応内容 |
|------|---------|
| パッケージ構造 | `src/aatable/__init__.py` 等を整備 |
| 共通モジュール化 | `display_width()` 等が 3 スクリプトに重複。共通モジュール `aatable/core.py` に切り出す |
| エントリポイント | `pyproject.toml` に `[project.scripts]` を定義 |
| テスト追加 | `pytest` + CI 整備 |
| バージョン管理 | `pyproject.toml` での semver 管理 |

### 12.6 ログ / 監視

CLI ツールのためログ・監視基盤は持たない。エラー出力は stderr へ書かれる。

| エラーケース | 出力 |
|------------|------|
| 有効なデータなし（aatable.py） | `Error: No valid tabular data found in input.` (stderr) + exit(1) |
| 非 TTY 環境（aacalibrate.py） | `Error: aacalibrate requires an interactive terminal.` (stderr) + exit(1) |

### 12.7 既知の制限と注意事項

| 制限 | 詳細 | 回避策 |
|------|------|--------|
| Windows ネイティブで aacalibrate 非対応 | `tty` / `termios` モジュールが存在しない | WSL を使用する、または `--ambiguous-width` を手動指定 |
| v0.4.0 の Ambiguous 幅プロファイル問題 | CLI デフォルト値がプロファイルを上書きする | `--ambiguous-width 2` を明示指定（macOS ユーザー） |
| `aafixwidth.py` の ZWJ 精度 | グラフェームクラスター分割を省略しているため、ZWJ シーケンスの幅計算が不正確になる場合がある | `aatable.py` を使用する（正規実装） |
| Mermaid の対応範囲 | サブグラフ、classDef、click ハンドラ等の高度な機能は非対応 | 非対応機能を使わない設計にする |
| `find_boxes()` デッドコード | `aafixwidth.py` に未使用関数が存在 | 現状のまま保持（将来利用の可能性あり） |
| 列単位アライメント非対応 | `--align` は全列に適用される | 列単位指定が必要な場合は post-process が必要 |
| プロファイルパスの固定 | `aatable.py` は `~/.aatable_profile.json` のみ読み込む | カスタムパスのプロファイルを使う場合は `--ambiguous-width` で上書き |
| stdin エンコーディング | UTF-8 ロケール環境を前提 | `PYTHONIOENCODING=utf-8` を設定する |

### 12.8 トラブルシューティング

#### 列がズレる（macOS Terminal.app）

macOS Terminal は Ambiguous 幅文字（`①`, `α`, `♠` 等）を幅 2 でレンダリングする。

```bash
python3 aacalibrate.py --quick
# または
python3 aatable.py --ambiguous-width 2 data.md
```

#### `graph-easy: command not found`

```bash
cpanm Graph::Easy
# または
curl -L https://cpanmin.us | perl - Graph::Easy
```

#### 絵文字の幅がおかしい

ZWJ シーケンスや国旗絵文字をサポートしていない古いターミナルでは、`aatable.py` の計算が正しくても表示がずれることがある。これはターミナルの限界であり、AATable のバグではない。

#### `aacalibrate.py` が "requires an interactive terminal" エラー

パイプ経由やスクリプト内から実行している。インタラクティブなターミナルエミュレータから直接実行する必要がある。

#### stdin に日本語が化ける

```bash
export PYTHONIOENCODING=utf-8
export LANG=ja_JP.UTF-8
```

---

*本文書は AATable v0.4.0 の実装（`aatable.py`, `aafixwidth.py`, `mmd2ge.py`, `aacalibrate.py`）を全量精査して作成された仕様書である。*
