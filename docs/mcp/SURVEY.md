# AATable — MCP 化調査 (Phase 1)

## 概要

AATable は Markdown / CSV / TSV の表形式データを CJK・絵文字・East Asian Ambiguous 文字に対応した ASCII Art テーブルに変換する Python CLI ツール群。標準ライブラリのみで依存ゼロ、Unix フィルタ設計。4 つのスクリプトで構成される:

| スクリプト | 役割 |
|---|---|
| `aatable.py` | Markdown / CSV / TSV → ASCII Art テーブル |
| `mmd2ge.py` | Mermaid フローチャート → Graph::Easy 形式（CJK 幅補正付き） |
| `aafixwidth.py` | 既存 ASCII Art の CJK 幅崩れを後処理で修正 |
| `aacalibrate.py` | ターミナルをプローブして Ambiguous 幅を自動検出 |

services.json には `id: "aatable"` (type: `cli`) として登録済みだが、host/port/MCP エントリは無い。

## 判定と理由

**判定: `library-serve`**

CLI ツールだが、MCP サーバ化して volta に参加させる価値がある。理由:

1. **組み合わせ価値**: 他サービス（DB クエリ結果・API レスポンス・ログ解析）の出力を JSON rows で受け取り、CJK 揃いの AA テーブルに変換する下流 tool として機能する。エージェントが「表をきれいに表示したい」ときに 1 tool で済む。
2. **常駐の価値**: 起動 1 秒以内の軽量処理だが、`_aawidth.py` のプロファイル読み込みとグラフェームクラスタ分割ロジックを常駐プロセスで保持することで、毎回の CLI 起動オーバーヘッドを省ける。また他サービスからの呼び出しレイテンシが安定する。
3. **重複なし**: volta カタログ（`catalog__list_services` / `svc_list`）に ASCII Art テーブル描画や CJK 幅計測を行う MCP サービスは存在しない。
4. **コスト小**: 標準ライブラリのみ・既存コードの薄いラップで済む。新規実装は MCP サーバ枠組み + healthz + manifest のみ（estimated: S）。

## 公開候補

| kind | name | io / uri | 副作用 | 長時間 | 対応コード |
|---|---|---|---|---|---|
| tool | `render_table` | rows (JSON) + opts → AA text | none | No | `aatable.py:render_aa_table()` |
| tool | `measure_width` | text + opts → {width, clusters} | none | No | `_aawidth.py:display_width()` |
| tool | `mmd2ge` | Mermaid text → Graph::Easy text | none | No | `mmd2ge.py:parse_mermaid()` |
| tool | `fix_width` | AA text + opts → corrected AA text | none | No | `aafixwidth.py:fix_aa_widths()` |
| resource | `spec` | `aatable://spec` | — | — | 機械可読仕様 |
| resource | `guide` | `aatable://guide` | — | — | 使い方 |
| resource | `styles` | `aatable://styles` | — | — | 枠線スタイル一覧 |
| skill | `ambiguous-calibration` | locality: repo | — | — | Ambiguous 幅判定とキャリブレーション手順 |

- すべて副作用なし（純粋なテキスト変換）。壊す系 tool は無いので dry-run は不要。
- 30 秒超の長時間処理は無い（job 型不要）。
- `aacalibrate.py` はインタラクティブ TTY が必須のため MCP tool には含めず、手順を skill として配る。

## 組み合わせ例

1. **vacant__query → aatable__render_table**: DB クエリ結果の JSON rows を CJK 揃いの AA テーブルにしてチャットに貼る
2. **index__agent_status → aatable__render_table**: エージェント稼働状況を表で整形して報告
3. **municipality__lookup → aatable__render_table**: 住所正規化結果を一覧表にしてレビュー

## 依存と協調

| 相手 | 方向 | 能力 | 現在あるか | 備考 |
|---|---|---|---|---|
| Graph::Easy (CPAN) | depends_on | `graph-easy --as=boxart`（mmd2ge 出力のレイアウト） | No | 外部 Perl モジュール。MCP tool の `mmd2ge` は Graph::Easy 形式テキストを返すだけ。boxart 化は呼び出し側で。volta 上に Graph::Easy MCP サービスは無い。 |

他の volta リポジトリが AATable の入口に依存している、あるいは AATable が他の MCP 入口に依存する、という協調は現時点ではない。

## ライブラリのサーバ化

| 項目 | 値 |
|---|---|
| needed | true |
| runtime | python |
| estimated_effort | S |
| 新規実装 | MCP サーバ（Streamable HTTP `/mcp`）, `/healthz` (200), `PORT` 環境変数（`0.0.0.0` bind）, `volta.service.json` manifest, systemd user unit / docker |

既存の `render_aa_table()` / `display_width()` / `fix_aa_widths()` / `parse_mermaid()` を薄くラップするだけで MCP tool になる。

## リスク

- **破壊的操作**: なし（純粋なテキスト変換のみ）
- **外部 API 課金**: なし（ネットワークアクセス一切なし）
- **graph-easy 依存**: mmd2ge tool は Graph::Easy 形式テキストを返すだけなので、サーバ本体に graph-easy は不要
- **Ambiguous 幅のターミナル依存**: MCP 経由で呼ぶエージェントのコンテキストに応じて `ambiguous_width` をパラメータで渡す設計にする必要がある。デフォルトは 1。
- **aacalibrate.py**: インタラクティブ TTY が必須のため MCP tool に含めない。手順は skill として配る。

## 持ち主への質問

1. `display_width` のみを独立 tool にするか、`render_table` に統合するか（単独でも他サービスから再利用されそうなら分ける）
2. `ambiguous_width` のデフォルトを 1（Windows 系）にするか 2（macOS 系）にするか、それとも必須パラメータにするか
3. services.json の既存 `aatable` エントリ（cli, host/port なし）を更新して MCP 対応にするか、別 env として追加するか
