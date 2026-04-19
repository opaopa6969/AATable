[English version](scripts.md)

# スクリプトリファレンス

AATable の 4 スクリプトの CLI リファレンスです。

---

## aatable.py

Markdown テーブル・CSV・TSV を、CJK 列整列が正確な ASCII Art テーブルに変換します。

### 書式

```
python3 aatable.py [OPTIONS] [FILE]
```

### 引数

| 引数   | 説明 |
|--------|------|
| `FILE` | 入力ファイルのパス。省略時は stdin から読み込みます。 |

### オプション

| オプション | 短縮形 | 値 | デフォルト | 説明 |
|------------|--------|----|-----------|------|
| `--format` | `-f` | `auto` `md` `csv` `tsv` | `auto` | 入力フォーマット。`auto` は内容から検出: `\|` で始まる行 → Markdown、タブ区切り → TSV、それ以外 → CSV。 |
| `--style` | `-s` | `single` `double` `bold` `round` `ascii` | `single` | 枠線文字セット。 |
| `--padding` | `-p` | 整数 | `1` | 各セルの内側に追加するスペース数 (左右それぞれ)。 |
| `--no-header` | — | フラグ | off | 先頭行をヘッダではなくデータとして扱います。0 行目の後に区切り線を描きません。 |
| `--ambiguous-width` | `-a` | `1` `2` | `1` (またはプロファイル) | Unicode Ambiguous 文字の表示幅。Windows Terminal / VS Code では `1`。macOS Terminal.app では `2`。`~/.aatable_profile.json` を上書きします。 |
| `--demo` | — | フラグ | off | 全文字種を含むデモテーブルと 5 種類のスタイルを表示します。`FILE` とフォーマットオプションは無視されます。 |

### 終了コード

| コード | 意味 |
|--------|------|
| 0 | 成功 |
| 1 | 入力に有効な表形式データが見つからない |

### フォーマット自動検出の順序

1. 空でない行が `|` で始まるものがある → **Markdown**
2. タブ文字を含む行がある → **TSV**
3. それ以外 → **CSV**

### 枠線スタイル

| 名前     | 使用文字 |
|----------|----------|
| `single` | `┌ ─ ┬ ┐ │ ├ ┼ ┤ └ ┴ ┘` |
| `double` | `╔ ═ ╦ ╗ ║ ╠ ╬ ╣ ╚ ╩ ╝` |
| `bold`   | `┏ ━ ┳ ┓ ┃ ┣ ╋ ┫ ┗ ┻ ┛` |
| `round`  | `╭ ─ ┬ ╮ │ ├ ┼ ┤ ╰ ┴ ╯` |
| `ascii`  | `+ - + + \| + + + + + +` |

### プロファイル自動読み込み

モジュールロード時に `aatable.py` は `~/.aatable_profile.json` (`aacalibrate.py` が生成) を読み込み、`ambiguous_width` フィールドから `_ambiguous_width` を設定します。`--ambiguous-width` CLI オプションはプロファイルを上書きします。

### 使用例

```bash
# stdin からの Markdown
echo '| a | b |
|---|---|
| 1 | 2 |' | python3 aatable.py

# CSV ファイル、round スタイル
python3 aatable.py -f csv --style round data.csv

# TSV、ヘッダなし、bold スタイル
cat data.tsv | python3 aatable.py -f tsv --no-header --style bold

# macOS Terminal、double スタイル
python3 aatable.py -f csv -a 2 --style double data.csv

# psql → テーブル
psql --csv -c "SELECT * FROM users LIMIT 10" mydb \
  | python3 aatable.py -f csv

# git log → テーブル
git log --format='%h,%s,%an' -5 \
  | python3 aatable.py -f csv --style round

# 全スタイルのデモ
python3 aatable.py --demo
```

---

## mmd2ge.py

Mermaid フローチャートを Graph::Easy 入力形式に変換します。CJK 文字の後にゼロ幅スペース (U+200B) を挿入することで、Graph::Easy が正しいサイズのボックスを割り当てられるようにします。

### 書式

```
python3 mmd2ge.py [FILE]
```

出力は `graph-easy` に直接パイプすることを想定しています。

### 引数

| 引数   | 説明 |
|--------|------|
| `FILE` | Mermaid フローチャートファイル。省略時 (または `-`) は stdin から読み込みます。 |

### サポートされる Mermaid 構文

| 機能 | 構文 |
|------|------|
| 方向 | `graph TD` / `graph LR` / `graph RL` / `graph BT` |
| 矩形ノード | `A[ラベル]` |
| 角丸矩形ノード | `A(ラベル)` |
| ダイヤモンドノード | `A{ラベル}` または `A{{ラベル}}` |
| 円形ノード | `A((ラベル))` |
| 有向エッジ | `A --> B` |
| ラベル付きエッジ | `A -- ラベル --> B` または `A -->|ラベル| B` |
| 点線エッジ | `A -.-> B` |
| 太線エッジ | `A ==> B` |
| 無向エッジ | `A --- B` |
| コメント | `%% コメント` |
| 複数ステートメント | `A --> B; B --> C` |

非サポート: サブグラフ、クリックハンドラ、classDef、style ディレクティブ。

### 出力形式

Graph::Easy 構文を出力します。方向が `down` 以外の場合は先頭に方向宣言が付きます:

```
graph { flow: right; }
[ 入力\u200b ] --> [ パース\u200b ]
[ パース\u200b ] -- OK --> [ 出力\u200b ]
```

### 使用例

```bash
# stdin からパイプで graph-easy へ
echo 'graph LR
A[Start] --> B[End]' | python3 mmd2ge.py | graph-easy --as=boxart

# ファイルから
python3 mmd2ge.py flow.mmd | graph-easy --as=boxart

# CJK ラベル付き
echo 'graph TD
A[入力] --> B{判定}
B -->|OK| C[完了]
B -->|NG| D[エラー]' | python3 mmd2ge.py | graph-easy --as=boxart
```

---

## aafixwidth.py

ASCII Art テキストの CJK 幅崩れを修正します。stdin またはファイルから読み込み、修正済みテキストを stdout に書き出します。

### 書式

```
python3 aafixwidth.py [OPTIONS] [FILE]
```

### 引数

| 引数   | 説明 |
|--------|------|
| `FILE` | 入力ファイル。省略時は stdin から読み込みます。 |

### オプション

| オプション | 短縮形 | 値 | デフォルト | 説明 |
|------------|--------|----|-----------|------|
| `--ambiguous-width` | `-a` | `1` `2` | `1` | Unicode Ambiguous 文字の表示幅。ターミナルに合わせてください。 |

### 修正の仕組み

1. 水平枠線 (`+----+----+`) を走査して列位置を特定する
2. コンテンツ行 (`| セル | セル |`) を `|` で分割し、各セルの `display_width()` を測定する
3. 末尾スペースをトリムする: `削除するスペース数 = display_width(content) - len(content)`

ボックス構造が検出されない場合は、シンプルな行ごとのアプローチにフォールバックします。

### 制限事項: find_boxes() デッドコード

`aafixwidth.py` には完全な矩形ボックスをトレースする `find_boxes()` 関数が含まれています。この関数は現在の実装では**呼ばれていません** — 実際のコードパスは `find_column_positions()` を使用しています。`find_boxes()` は保存されていますが到達不能です。

### 使用例

```bash
# graph-easy の出力をその場で修正
graph-easy input.dot | python3 aafixwidth.py

# 保存済み ASCII Art ファイルを修正
python3 aafixwidth.py broken-aa.txt

# macOS の Ambiguous 幅で修正
cat broken-aa.txt | python3 aafixwidth.py -a 2
```

---

## aacalibrate.py

テスト文字をターミナルに書き込み、ANSI DSR (`\033[6n`) でカーソル位置を照会することで、ターミナルの実際の文字レンダリング幅をプローブします。`aatable.py` が自動読み込みする JSON プロファイルを保存します。

### 書式

```
python3 aacalibrate.py [OPTIONS]
```

インタラクティブな TTY が必要です。パイプ不可。

### オプション

| オプション | 短縮形 | 値 | デフォルト | 説明 |
|------------|--------|----|-----------|------|
| `--output` | `-o` | パス | `~/.aatable_profile.json` | プロファイル出力パス。 |
| `--quick` | `-q` | フラグ | off | 高速モード: Ambiguous と絵文字のみをプローブします (高速)。 |
| `--json` | — | フラグ | off | プロファイル JSON を出力ファイルではなく stdout に書き出します。 |
| `--quiet` | — | フラグ | off | stderr への進捗出力をすべて抑制します。 |

### プロファイル形式

```json
{
  "terminal": {
    "TERM": "xterm-256color",
    "TERM_PROGRAM": "iTerm.app",
    "WT_SESSION": false,
    "LANG": "ja_JP.UTF-8",
    "WSL_DISTRO_NAME": ""
  },
  "ambiguous_width": 2,
  "probe_results": {
    "ambiguous": [
      { "char": "①", "name": "Circled Digit 1", "eaw": "A", "measured_width": 2 },
      ...
    ],
    ...
  }
}
```

`ambiguous_width` フィールドはコンセンサス値です (全 Ambiguous 測定値の平均 > 1.5 → 2、それ以外 → 1)。

### aatable.py による自動読み込み

`aatable.py` はインポート時に `_load_ambiguous_width_from_profile()` を呼び出します。`~/.aatable_profile.json` が存在し有効な JSON であれば、`ambiguous_width` が読み込まれます。この値がデフォルトで、CLI の `--ambiguous-width` で上書きできます。

### 使用例

```bash
# フルプローブ、デフォルトパスに保存
python3 aacalibrate.py

# 高速プローブ (Ambiguous + 絵文字のみ)
python3 aacalibrate.py --quick

# カスタムパスに保存
python3 aacalibrate.py -o ~/my-terminal-profile.json

# stdout に JSON を出力 (確認用)
python3 aacalibrate.py --json --quiet
```
