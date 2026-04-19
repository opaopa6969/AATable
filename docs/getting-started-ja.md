[English version](getting-started.md)

# はじめに

---

## 要件

- Python 3.8 以上 (標準ライブラリのみ — pip インストール不要)
  - Python 3.8 は 2024 年 10 月に EOL を迎えています。Python 3.9+ を推奨します。
- `mmd2ge.py` を使う場合: [Graph::Easy](https://metacpan.org/pod/Graph::Easy) Perl モジュール
- `aacalibrate.py` を使う場合: インタラクティブな TTY (パイプ不可)

---

## インストール

```bash
git clone https://github.com/opaopa6969/AATable.git
cd AATable
chmod +x aatable.py aafixwidth.py mmd2ge.py aacalibrate.py
```

仮想環境不要、依存なし、ビルドステップなし。

Mermaid フローチャートサポートのために Graph::Easy をインストールする場合:

```bash
cpanm Graph::Easy       # cpanminus 経由
# または
perl -MCPAN -e 'install Graph::Easy'
```

---

## 最初のステップ

### 1. Python バージョンを確認

```bash
python3 --version
# Python 3.9.x 以上を推奨
```

### 2. 組み込みデモを実行

```bash
python3 aatable.py --demo
```

ASCII・CJK・全角・半角・Ambiguous・絵文字が混在したテーブルと、5 種類のスタイルが表示されます。

### 3. Markdown テーブルをパイプで渡す

```bash
echo '| name     | age | city     |
|----------|-----|----------|
| 田中太郎 | 30  | 東京     |
| Alice    | 25  | New York |
| 鈴木①    | 42  | 大阪     |' | python3 aatable.py
```

期待される出力:

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

### 4. ターミナルのキャリブレーション (任意、推奨)

`①` や `α` を 2 幅でレンダリングするターミナルを使っている場合、一度だけ実行します:

```bash
python3 aacalibrate.py --quick
```

キャリブレーション後は、`aatable.py` が毎回起動時に正しい `--ambiguous-width` を自動設定します。

---

## 基本ワークフロー: aatable.py

### Markdown 入力

```bash
# stdin から
cat table.md | python3 aatable.py

# ファイルから
python3 aatable.py table.md
```

### CSV 入力

```bash
python3 aatable.py -f csv data.csv
cat data.csv | python3 aatable.py -f csv
```

### TSV 入力

```bash
python3 aatable.py -f tsv data.tsv
cat data.tsv | python3 aatable.py -f tsv
```

### 自動検出 (デフォルト)

```bash
cat anything | python3 aatable.py
# Markdown → TSV → CSV の順で試みる
```

### スタイル指定

```bash
python3 aatable.py --style double data.csv
python3 aatable.py --style bold   data.csv
python3 aatable.py --style round  data.csv
python3 aatable.py --style ascii  data.csv
```

### macOS Terminal (Ambiguous = 2)

```bash
python3 aatable.py --ambiguous-width 2 data.md
# または: aacalibrate.py を一度実行してフラグを省略
```

---

## ワークフロー: mmd2ge.py + graph-easy

Mermaid フローチャートを CJK ボックスサイズ正確な ASCII Art に変換します。

### 基本パイプライン

```bash
cat flow.mmd | python3 mmd2ge.py | graph-easy --as=boxart
```

### ファイルから

```bash
python3 mmd2ge.py flow.mmd | graph-easy --as=boxart
```

### Mermaid 入力例

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

## ワークフロー: aafixwidth.py

すでに持っている ASCII Art の CJK 幅崩れを修正します。

```bash
# graph-easy の出力を直接修正
graph-easy input.dot | python3 aafixwidth.py

# 保存済みファイルを修正
python3 aafixwidth.py broken-aa.txt

# stdin から修正
cat broken-aa.txt | python3 aafixwidth.py
```

---

## 実用パイプライン

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

## トラブルシューティング

### macOS Terminal.app で列がズレる

macOS Terminal は Ambiguous 幅文字 (`①`、`α`、`♠` 等) を 2 幅でレンダリングします。  
キャリブレーションを実行するか、フラグを追加してください:

```bash
python3 aacalibrate.py --quick
# または
python3 aatable.py --ambiguous-width 2 data.md
```

### `graph-easy: command not found`

Graph::Easy をインストールします:

```bash
cpanm Graph::Easy
```

`cpanm` がない場合:

```bash
curl -L https://cpanmin.us | perl - Graph::Easy
```

### 絵文字の表示がまだ崩れる

古いターミナルの中には、ZWJ シーケンスや国旗インジケータペアを 1 グリフとして扱わないものがあります。`aatable.py` の出力は、それらを 1 グリフとしてレンダリングするターミナルに対しては正確です。ターミナルの扱いが異なる場合、どうしても崩れます — これはターミナルの制限であり、バグではありません。

### aacalibrate.py が "requires an interactive terminal" で失敗する

`aacalibrate.py` は TTY に直接書き込み・読み込みを行います。パイプ不可です。  
スクリプト内ではなく、ターミナルエミュレータで直接実行してください。
