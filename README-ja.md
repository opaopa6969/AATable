[English version](README.md)

# AATable

Markdown / CSV / TSV の表形式データを、美しく整列した ASCII Art テーブルに変換します。  
**CJK・絵文字・East Asian Ambiguous 幅**に完全対応しており、等幅フォントのターミナルでも列がきちんと揃います。

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

---

## 目次

- [なぜ AATable が必要か](#なぜ-aatable-が必要か)
- [クイックスタート](#クイックスタート)
- [スクリプト一覧](#スクリプト一覧)
- [使用例](#使用例)
- [枠線スタイル](#枠線スタイル)
- [CJK 幅の処理](#cjk-幅の処理)
- [仕組み](#仕組み)
- [オプション一覧](#オプション一覧)

---

## なぜ AATable が必要か

テーブルを描くツールのほとんどは、列幅の計算に `len()` を使います。  
`len("田中")` は `2` を返します。しかし `田中` は等幅ターミナルで **4 列** を占有します。  
結果: 枠線がズレる、セルからはみ出す、テーブルが崩れる。

AATable は `len()` を適切な `display_width()` に置き換えます:

| 文字種           | 例        | `len()` | `display_width()` |
|------------------|-----------|---------|-------------------|
| ASCII            | `Hello`   | 5       | 5                 |
| CJK              | `漢字`    | 2       | **4**             |
| 全角英数         | `Ａ１`    | 2       | **4**             |
| 半角カナ         | `ｱｲｳ`   | 3       | 3                 |
| Ambiguous        | `①α♠`    | 3       | 3 または **6**    |
| 絵文字           | `😀🎉`    | 2       | **4**             |
| ZWJ シーケンス   | `👨‍👩‍👧`     | 7 (!)   | **2**             |
| 国旗             | `🇯🇵`    | 2       | **2**             |

---

## クイックスタート

```bash
# 依存なし — Python 3.8+ のみ
# (Python 3.8 は 2024 年 10 月に EOL。Python 3.9+ を推奨)
git clone https://github.com/opaopa6969/AATable.git
cd AATable
chmod +x aatable.py aafixwidth.py mmd2ge.py aacalibrate.py
```

表形式データをパイプで渡すだけ:

```bash
echo '| 名前     | 年齢 |
|----------|------|
| 田中太郎 | 30   |
| Alice    | 25   |' | python3 aatable.py
```

---

## スクリプト一覧

| スクリプト        | 役割                                                        |
|-------------------|-------------------------------------------------------------|
| `aatable.py`      | Markdown / CSV / TSV → ASCII Art テーブル                   |
| `mmd2ge.py`       | Mermaid フローチャート → Graph::Easy 形式 (CJK 幅補正付き) |
| `aafixwidth.py`   | 既存 ASCII Art の CJK 幅崩れを後処理で修正                  |
| `aacalibrate.py`  | ターミナルをプローブして Ambiguous 幅を自動検出             |

---

## 使用例

### aatable.py — 表形式データを ASCII Art に

```bash
# Markdown テーブル (stdin)
echo '| a | b |
|---|---|
| 1 | 2 |' | python3 aatable.py

# CSV ファイル
python3 aatable.py -f csv data.csv

# psql の出力をそのままテーブルに
psql --csv -c "SELECT name, age FROM users LIMIT 5" mydb \
  | python3 aatable.py -f csv

# git log をテーブル表示
git log --format='%h,%s,%an' -5 \
  | python3 aatable.py -f csv --style round

# docker ps
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' \
  | python3 aatable.py -f tsv --style bold --no-header

# curl + jq
curl -s https://api.example.com/data \
  | jq -r '["id","name"], (.[] | [.id,.name]) | @csv' \
  | python3 aatable.py -f csv

# 全スタイルのデモを表示
python3 aatable.py --demo
```

### mmd2ge.py — Mermaid フローチャートを ASCII Art に

Mermaid のフローチャート構文を [Graph::Easy](https://metacpan.org/pod/Graph::Easy) 入力形式に変換します。  
CJK 文字の後にゼロ幅スペース (U+200B) を挿入することで、`len()` と `display_width()` を一致させます。

```bash
# Graph::Easy を一度インストール
cpanm Graph::Easy

# Mermaid → ASCII Art パイプライン
echo 'graph LR
A[入力] --> B[パース]
B --> C{判定}
C -->|OK| D[出力]
C -->|NG| E[エラー]' | python3 mmd2ge.py | graph-easy --as=boxart
```

出力:

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

### aafixwidth.py — 崩れた ASCII Art を修正

CJK 非対応ツールで生成済みの ASCII Art に対して:

```bash
graph-easy broken.dot | python3 aafixwidth.py
cat broken-aa.txt | python3 aafixwidth.py
```

### aacalibrate.py — ターミナルの Ambiguous 幅を検出

一度だけ実行してプロファイルを保存します:

```bash
python3 aacalibrate.py          # フルプローブ → ~/.aatable_profile.json
python3 aacalibrate.py --quick  # 高速: Ambiguous + 絵文字のみ
```

`aatable.py` は起動時に `~/.aatable_profile.json` を自動読み込みするため、  
毎回 `--ambiguous-width` を指定する必要がなくなります。

---

## 枠線スタイル

| スタイル   | 文字                                   |
|------------|----------------------------------------|
| `single`   | `┌─┬─┐ │ ├─┼─┤ └─┴─┘` (デフォルト)   |
| `double`   | `╔═╦═╗ ║ ╠═╬═╣ ╚═╩═╝`               |
| `bold`     | `┏━┳━┓ ┃ ┣━╋━┫ ┗━┻━┛`               |
| `round`    | `╭─┬─╮ │ ├─┼─┤ ╰─┴─╯`               |
| `ascii`    | `+-+-+ \| +-+-+ +-+-+`               |

```bash
python3 aatable.py --style double data.csv
python3 aatable.py --style round  data.csv
```

---

## CJK 幅の処理

### East Asian Width カテゴリ

Unicode はすべての文字に [East Asian Width](https://unicode.org/reports/tr11/) プロパティを定義しています:

| EAW | 名称       | 幅 | 例               |
|-----|------------|----|------------------|
| W   | Wide       | 2  | CJK・ひらがな・ハングル |
| F   | Fullwidth  | 2  | `Ａ` `１` `！`  |
| Na  | Narrow     | 1  | ASCII            |
| H   | Halfwidth  | 1  | `ｱ` `ｲ` `ｳ`   |
| A   | Ambiguous  | **?** | `①` `α` `♠` `—` |
| N   | Neutral    | 1  | その他記号       |

### Ambiguous 問題

Unicode は Ambiguous カテゴリを「ターミナル依存」と定義しています:

| ターミナル                    | Ambiguous 幅 |
|-------------------------------|-------------|
| Windows Terminal、VS Code     | 1 (デフォルト) |
| macOS Terminal.app、iTerm2    | 2           |

macOS Terminal を使う場合は `--ambiguous-width 2` を指定するか、  
`aacalibrate.py` を一度実行して自動検出してください。

### 絵文字と書記素クラスタ

`len("👨‍👩‍👧") = 7` — ZWJ で結合された 7 つのコードポイント。  
`display_width("👨‍👩‍👧") = 2` — 1 グリフ、2 列分。

AATable は書記素クラスタ分割を実装しており、ZWJ シーケンス・国旗ペア (`🇯🇵`)・  
スキントーン修飾シーケンスをすべて 1 クラスタとして正しく扱います。

---

## 仕組み

### aatable.py — 幅認識テーブルレンダラー

1. **パース** — フォーマット検出 (Markdown / CSV / TSV) と行の抽出
2. **書記素クラスタ分割** — 各セルを視覚的単位に分割 (ZWJ シーケンス等を 1 クラスタとして扱う)
3. **East Asian Width 参照** — コードポイントごとに `unicodedata.east_asian_width()` を呼ぶ
4. **`pad_to_width()`** — `len()` ではなく `display_width()` に基づいてスペースでパディング
5. **レンダリング** — 正しいサイズのセルの周囲に枠線文字を組み立て

### mmd2ge.py — ゼロ幅スペーストリック

Graph::Easy は Perl 製のグラフレイアウト・ASCII Art ツールです。  
他の多くのツールと同様、ボックス幅の計算に `len()` を使います。  
`入` は 1 文字ですが、ターミナルで 2 列を占有します:

```
+----+       ← len("入力") = 2、枠線 = 2 + パディング 2 = 4
| 入力 |     ← しかし "入力" は 4 列でレンダリング → はみ出し！
+----+
```

修正方法: 全角文字の後に U+200B (ゼロ幅スペース) を挿入します。  
U+200B は表示されませんが `len()` のカウントに加算されます:

```python
"入力"              # len=2, display_width=4  — 不一致
"入\u200b力\u200b"  # len=4, display_width=4  — 一致
```

Graph::Easy へのパッチ不要。Unix 的アプローチ: ツールではなくデータを直す。

### aafixwidth.py — 後処理フィクサー

すでに CJK 非対応でレンダリングされた ASCII Art に対して、  
ボックス構造を読み取り、セル内容の実際の表示幅を測定し、  
末尾スペースをトリムして整列を復元します。

### aacalibrate.py — カーソル位置プローブ

テスト文字をターミナルに書き込み、ANSI DSR (`\033[6n`) でカーソル位置を照会し、  
列差分を測定します。結果を `~/.aatable_profile.json` に保存。  
`aatable.py` は起動時にこのファイルを読み込みます。

---

## オプション一覧

### aatable.py

```
usage: aatable.py [-h] [-f {auto,md,csv,tsv}] [-s STYLE] [-p PADDING]
                  [--no-header] [-a {1,2}] [--demo] [file]

positional arguments:
  file                    入力ファイル (省略時: stdin)

options:
  -f, --format            入力フォーマット: auto|md|csv|tsv (デフォルト: auto)
  -s, --style             枠線スタイル: single|double|bold|round|ascii (デフォルト: single)
  -p, --padding           セル内のスペース数 (デフォルト: 1)
  --no-header             先頭行をヘッダとして扱わない
  -a, --ambiguous-width   Ambiguous 文字の幅: 1|2 (デフォルト: 1)
  --demo                  全文字種・全スタイルのデモを表示
```

### mmd2ge.py

```
usage: mmd2ge.py [file]

Mermaid フローチャートをファイルまたは stdin から読み込み、
Graph::Easy 形式で出力します。
出力先: graph-easy --as=boxart にパイプ
```

### aafixwidth.py

```
usage: aafixwidth.py [-h] [-a {1,2}] [file]

positional arguments:
  file                    入力ファイル (省略時: stdin)

options:
  -a, --ambiguous-width   Ambiguous 文字の幅: 1|2 (デフォルト: 1)
```

### aacalibrate.py

```
usage: aacalibrate.py [-h] [-o OUTPUT] [-q] [--json] [--quiet]

options:
  -o, --output            プロファイル出力パス (デフォルト: ~/.aatable_profile.json)
  -q, --quick             高速モード: Ambiguous + 絵文字のみ
  --json                  プロファイル JSON を stdout に出力
  --quiet                 進捗出力を抑制
```

---

## ライセンス

MIT
