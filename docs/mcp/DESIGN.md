# AATable MCP 設計（Phase 2）

> Phase 1 survey: `docs/mcp/survey.json` / 割当表: `docs/MCPIFY-phase2-plan.md` 行 #57

## 1. namespace と種別

- **namespace**: `aatable`
- **種別**: `library-serve`（CLI ツール群を MCP サーバとして常駐化）
- **port**: 9251（割当表指定。`volta__machine_ports` で空き確認済み）
- **host**: 192.168.1.50（prod）

## 2. tools 表

全 tool は純粋関数（副作用 none）。破壊的操作なし。dry-run / confirm 不要。job 型なし（全て即応答）。

| name | 目的 | 入力 schema（要点） | 出力の形 | 副作用 | job型 | 所要時間 | min_role |
|---|---|---|---|---|---|---|---|
| `render_table` | JSON rows を CJK 揃いの ASCII Art テーブルに変換 | `rows: array<array<string>>`, `style: enum(single,double,bold,ascii,round)=single`, `padding: int=1`, `align: enum(left,right,center)=left`, `header: bool=true`, `ambiguous_width: enum(1,2)=1` | `{table: string}` | none | no | <10ms | VIEWER |
| `measure_width` | 文字列の表示幅と grapheme クラスタ数を計測 | `text: string`, `ambiguous_width: enum(1,2)=1` | `{display_width: int, grapheme_clusters: int}` | none | no | <1ms | VIEWER |
| `mmd2ge` | Mermaid フローチャートを Graph::Easy 形式テキストに変換 | `mermaid: string` | `{graph_easy: string, direction: string}` | none | no | <1ms | VIEWER |
| `fix_width` | 既存 ASCII Art の CJK 幅ずれを修正 | `text: string`, `ambiguous_width: enum(1,2)=1` | `{fixed: string}` | none | no | <1ms | VIEWER |
| `list_styles` | サポートする枠線スタイル一覧を返す | なし | `{styles: array<{name, sample}>}` | none | no | <1ms | VIEWER |

### 設計判断

- **`render_table` と `measure_width` は分離**: `measure_width` は他サービス（DB 統計・ログ解析）から単独で再利用される（survey の open_question #1 の解決）。独立 tool にする。
- **`ambiguous_width` のデフォルトは 1**: MCP 経由のエージェントはターミナルコンテキスト不明。1（narrow）を既定とし、呼び出し側で 2 を明示できる（survey open_question #2 の解決）。必須パラメータにはしない（既定で動く）。
- **`aacalibrate` は tool に含めない**: TTY 必須のインタラクティブツール。skill として手順を配る（survey の記載通り）。
- **全 tool に `readOnlyHint: true`**: 破壊的操作なし。`destructiveHint` / `idempotentHint` は不要。

## 3. resources 表

| uri | 内容 | mime |
|---|---|---|
| `aatable://spec` | サーバの能力一覧（JSON。tools/list から自動生成＋compositions/depends_on 手動追記） | application/json |
| `aatable://guide` | 使い方ガイド（Markdown） | text/markdown |
| `aatable://styles` | サポートする枠線スタイル一覧とサンプル | application/json |

## 4. prompts / skills

### skill: `ambiguous-calibration`

- **用途**: Ambiguous 文字幅がターミナル依存であることの説明と、`aacalibrate.py` でのキャリブレーション手順
- **locality**: `repo`（このリポジトリ固有）
- **applies_when**: Ambiguous 幅の違いで表のズレに気づいたとき
- **requires**: なし（手順の読み物）
- **min_role**: VIEWER
- **配置**: `docs/skills/ambiguous-calibration/SKILL.md` + resource `skill://ambiguous-calibration`

## 5. 組み合わせ例

1. **DB 統計を表で整形**: `mstats__all_indicators(lgCode, year)` → `aatable__render_table(rows=結果, header=true)` → チャットに貼る
2. **住所パーサ比較結果の可視化**: `jbench__rows(runset, view=split)` → rows を変換 → `aatable__render_table` → レビュー用一覧表
3. **Mermaid 図を Graph::Easy 経由で描画**: `aatable__mmd2ge(mermaid)` → Graph::Easy 形式テキスト → 別途 `graph-easy` コマンドで boxart 化

## 6. 依存と協調

| 相手 repo | 依存方向 | 入口 | 合意したいこと |
|---|---|---|---|
| Graph::Easy (CPAN) | depends_on | 外部 Perl モジュール `graph-easy --as=boxart` | `mmd2ge` tool は Graph::Easy **形式テキスト**を返すだけ。boxart 化は呼び出し側で行う。volta 上に Graph::Easy MCP サービスは無く、新設もしない。外部 CLI 依存は MCP の範囲外。 |

issue-hub への登録: 不要（他リポジトリの MCP 入口に依存しない。Graph::Easy は外部 Perl モジュールであり、MCP 協調対象ではない）。

## 7. 非対応にした候補

| 候補 | 理由 |
|---|---|
| `aacalibrate` を tool 化 | TTY 必須のインタラクティブ処理。MCP tool に不向き。skill として手順を配る。 |
| `parse_md_table` / `parse_csv` / `parse_auto` を独立 tool 化 | `render_table` が JSON rows を受け取る設計なので、パースは呼び出し側で行う。CLI の `aatable.py` は Markdown/CSV/TSV をパースするが、MCP では構造化データを受ける。 |

## 8. 参加方法

### manifest (`volta.service.json`)

```json
{
  "id": "aatable",
  "name": "AATable MCP",
  "description": "Markdown/CSV/TSV を CJK・絵文字対応の ASCII Art テーブルに変換する MCP サーバ",
  "type": "python",
  "hostname": "aatable.unlaxer.org",
  "port": 9251,
  "host": "192.168.1.50",
  "runtime": "systemd",
  "exec_start": "/home/opa/aatable/run.sh",
  "user": "opa",
  "auth": "minRole:VIEWER",
  "health_check": "/healthz",
  "tags": ["mcp", "formatting", "cjk", "ascii-art", "library", "opa"],
  "repo_url": "https://github.com/opaopa6969/AATable",
  "mcp": {
    "enabled": true,
    "port": 9251,
    "path": "/mcp",
    "namespace": "aatable",
    "min_role": "VIEWER",
    "timeoutMs": 110000,
    "description": "CJK・絵文字対応 ASCII Art テーブル描画・幅計測・Mermaid→Graph::Easy 変換"
  }
}
```

### runtime

- **言語**: Python 3.13（標準ライブラリのみ + `mcp` SDK + `uvicorn` + `starlette`）
- **systemd user unit**: `deploy/aatable.service`（`WantedBy=default.target`, `Restart=on-failure`, `Environment=PORT=9251`）
- **run.sh**: `python3 mcp/server.py`（`PORT` 環境変数でポート指定）
- **auth**: public（`minRole:VIEWER`、送信元 IP 制限は gateway 側）

## 9. テスト方針

e2e テスト（`tests/test_mcp_server.py`）:

1. サーバ起動（サブプロセス、`PORT` を空きポートに設定）
2. `GET /healthz` → 200, `{ok: true, name, version}`
3. MCP 初期化 → `tools/list` → 5 tools が見える
4. `render_table` に CJK 含み rows を渡す → 整形された AA テキスト
5. `measure_width` に CJK + 絵文字 → 正しい幅
6. `mmd2ge` に Mermaid テキスト → Graph::Easy 形式
7. `fix_width` にずれた AA → 修正済み
8. `list_styles` → 5 スタイル
9. `resources/read` で `aatable://spec` → JSON
10. `resources/read` で `aatable://guide` → Markdown

テストは MCP クライアント（`mcp` SDK の `Client` + `StreamableHTTPClientTransport`）で実行。
