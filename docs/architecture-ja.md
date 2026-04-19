[English version](architecture.md)

# アーキテクチャ

AATable は 4 つの Python スクリプトで構成されています。  
それぞれが組み合わせ可能な Unix フィルタです — stdin またはファイルから読み込み、stdout に書き出し、1 つのことを確実に行います。

---

## スクリプトの役割

```
aacalibrate.py   ──→  ~/.aatable_profile.json
                                │
                                ▼
stdin/file  ──→  aatable.py  ──→  stdout   (テーブルレンダリング)

stdin/file  ──→  mmd2ge.py   ──→  graph-easy  ──→  aafixwidth.py  ──→  stdout
                 (Mermaid→GE)     (レイアウト)      (CJK 修正)
```

| スクリプト       | 入力                | 出力                      | 依存           |
|------------------|---------------------|---------------------------|----------------|
| `aatable.py`     | Markdown/CSV/TSV    | ASCII Art テーブル        | 標準ライブラリのみ |
| `mmd2ge.py`      | Mermaid フローチャート | Graph::Easy 形式        | 標準ライブラリのみ |
| `aafixwidth.py`  | ASCII Art テキスト  | 幅補正済みテキスト        | 標準ライブラリのみ |
| `aacalibrate.py` | ターミナル (TTY 必須) | `~/.aatable_profile.json` | `tty`, `termios` |

4 スクリプトすべて **Python 3.8+** が必要 (pip インストール不要)。  
Python 3.8 は 2024 年 10 月に EOL を迎えています。Python 3.9+ を推奨します。

---

## コア: `display_width()` と `pad_to_width()`

AATable が解決する根本的な問題は、Python の `len()` がターミナルの列数ではなくコードポイント数を返すことです。

### `display_width(text: str) -> int`

`aatable.py` に正規実装があり、`aafixwidth.py` と `mmd2ge.py` に若干の変形で重複実装されています。

アルゴリズム:

1. `split_grapheme_clusters(text)` で視覚的単位に分割
2. 各クラスタに対して `grapheme_width(cluster)` を呼ぶ
3. 幅を合計する

### `split_grapheme_clusters(text: str) -> List[str]`

手書きの書記素クラスタ分割器です。UAX #29 の完全実装ではありませんが、  
実際の幅計算ミスを引き起こすケースをカバーしています:

| シーケンス種別          | 例        | コードポイント数 | クラスタ数 | 幅 |
|-------------------------|-----------|----------------|------------|-----|
| ASCII                   | `AB`      | 2              | 2          | 2   |
| CJK                     | `漢字`    | 2              | 2          | 4   |
| ZWJ シーケンス          | `👨‍👩‍👧`   | 7              | 1          | 2   |
| 国旗インジケータペア    | `🇯🇵`   | 2              | 1          | 2   |
| 絵文字 + スキン修飾     | `👋🏽`   | 2              | 1          | 2   |
| 絵文字 + 異体字セレクタ | `☺️`      | 2              | 1          | 2   |

### `grapheme_width(cluster: str) -> int`

以下の順序でルールを適用します:

1. クラスタに U+200D (ZWJ) が含まれる → 幅 2 (単一絵文字グリフ)
2. 先頭コードポイントが国旗インジケータ → 幅 2 (国旗)
3. 先頭コードポイントが絵文字ベース → 幅 2
4. それ以外 → 基底文字の `unicodedata.east_asian_width()`

### `pad_to_width(text: str, target_width: int, align: str = 'left') -> str`

`text` の `display_width()` が `target_width` になるまで ASCII スペースでパディングします。

```python
pad_to_width("田中", 8)          # "田中    "  (全角 4 + スペース 4 = 8)
pad_to_width("Alice", 8)         # "Alice   "  (5 文字 + スペース 3 = 8)
pad_to_width("田中", 8, "right") # "    田中"
```

これが列の整列を実現する関数です。

---

## East Asian Width と Ambiguous 問題

Unicode TR11 は 6 つの East Asian Width カテゴリを定義しています:

| カテゴリ     | 幅 | 備考                                        |
|--------------|-----|---------------------------------------------|
| W (Wide)     | 2   | CJK・ひらがな・カタカナ・ハングル           |
| F (Fullwidth) | 2  | `Ａ`、`１`、`！`                            |
| Na (Narrow)  | 1   | ASCII、ラテン文字                            |
| H (Halfwidth) | 1  | `ｱ`、`ｲ`、`ｳ`                             |
| A (Ambiguous) | **?** | ターミナル依存。下記参照                 |
| N (Neutral)  | 1   | 上記以外のほとんどの記号                    |

### Ambiguous カテゴリ

Unicode は Ambiguous 幅を「コンテキスト依存」と定義しています。各ターミナルの扱いは異なります:

- **Windows Terminal、VS Code、多くのモダンターミナル**: 幅 = 1
- **macOS Terminal.app、iTerm2 (CJK ロケール)**: 幅 = 2

影響を受ける文字: `①②③`、`αβγ`、`♠♥♦♣`、`—`、`±`、`×`、`÷`、`°` など。

`aatable.py` のデフォルトは `--ambiguous-width 1` です。macOS Terminal では  
`--ambiguous-width 2` を指定するか、`aacalibrate.py` を一度実行して自動検出・保存してください。

モジュールレベル変数 `_ambiguous_width` は CLI パース時に設定されます:

```python
global _ambiguous_width
_ambiguous_width = args.ambiguous_width
```

---

## mmd2ge.py: ゼロ幅スペーストリック

Graph::Easy は CPAN モジュールで、ボックス幅の計算に Perl の `length()` を使います。  
これは Python の `len()` 相当です。CJK 文字は 1 コードポイントですが、2 ターミナル列を占有します:

```
修正なし:
+----+       ← length("入力") = 2、枠線 = 4 (2 + パディング 2)
| 入力 |     ← しかし "入力" は 4 列 → 右の枠線が 4 ではなく 5 列目に
+----+
```

トリック: 全角文字の後に U+200B (ゼロ幅スペース) を追加します。  
U+200B は表示幅 0 ですが、`len()` のカウントには加算されます:

```python
"入力"              # len=2, display_width=4 — 不一致
"入\u200b力\u200b"  # len=4, display_width=4 — 一致
```

`mmd2ge.py` の `pad_for_grapheasy(label)` は全角文字をカウントして同数の U+200B を追加します:

```python
def pad_for_grapheasy(label: str) -> str:
    extra = sum(1 for ch in label if char_display_width(ch) == 2)
    return label + '\u200b' * extra
```

このアプローチは `len()` ベースのどんなツールとも組み合わせられます。パッチ不要。

---

## aafixwidth.py: 後処理戦略

すでに誤った幅でレンダリングされた ASCII Art に対して、`aafixwidth.py` は異なる戦略を取ります:

1. 水平枠線 (`+----+----+`) から**列位置を検出**する
2. 各コンテンツ行を `|` で分割し、各セグメントの `display_width()` を測定する
3. `display_width(content) - len(content)` (全角文字の余剰分) に等しい末尾スペースをトリムする

これはソースから再レンダリングするよりもシンプルで堅牢です。ソースが入手できない場合にも使えます。

### `find_boxes()` — デッドコードについて

`aafixwidth.py` には、`+` コーナーから完全な矩形ボックスをトレースする `find_boxes()` 関数が含まれています。  
この関数は**現在の実装では呼ばれていません** — `fix_aa_widths()` はよりシンプルな  
`find_column_positions()` アプローチを使用しています。`find_boxes()` は過剰設計と判断されましたが、  
将来的な利用に備えて保存されています。現状では到達不能なコードです。

---

## aacalibrate.py: ターミナルプローブ

`aacalibrate.py` はインタラクティブな TTY が必要です (パイプ不可)。処理の流れ:

1. `tty.setraw()` / `termios` でターミナルをローモードに設定
2. 各テスト文字について: カーソルを移動、文字を書き込み、ANSI DSR (`\033[6n`) で位置照会、`\033[row;colR` レスポンスを読む
3. 列差分 = レンダリング幅
4. すべての Ambiguous 文字の測定値を集計し、コンセンサスを計算 (平均 > 1.5 → 幅 2)
5. `{ ambiguous_width: N, probe_results: {...}, terminal: {...} }` を `~/.aatable_profile.json` に保存

`aatable.py` はモジュールロード時にプロファイルを読み込みます:

```python
_ambiguous_width = _load_ambiguous_width_from_profile()
```

---

## データフロー概要

```
入力テキスト
    │
    ▼
split_grapheme_clusters()   — 視覚的単位への分割
    │
    ▼  (クラスタのリスト)
grapheme_width()            — クラスタごとの EAW 参照
    │
    ▼  (整数幅)
pad_to_width()              — 列幅までスペースパディング
    │
    ▼  (パディング済みセル文字列)
render_aa_table()           — 枠線文字の組み立て
    │
    ▼
stdout
```
