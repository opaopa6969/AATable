# AATable MCP 化ステータス（Phase 2）

## 進捗サマリー

| 項目 | 状態 |
|---|---|
| Phase 1 survey | done (`docs/mcp/survey.json`) |
| 設計 (DESIGN.md) | done |
| MCP サーバ実装 | done (`mcp/server.py`) |
| e2e テスト | done (`tests/test_mcp_server.py`, 11 tests, all pass) |
| volta.service.json | done |
| deploy unit + run.sh | done |
| skill (SKILL.md) | done (`docs/skills/ambiguous-calibration/SKILL.md`) |
| README MCP 節 | done |
| commit & push | pending |
| volta 登録 (svc_add) | pending |
| gateway ルート適用 | pending |
| healthz 200 確認 | pending |
| catalog backend ready 確認 | pending |

## 実装内容

### namespace: `aatable`, port: 9251

- **種別**: library-serve（CLI ツール群を MCP サーバとして常駐化）
- **言語**: Python 3.13 + mcp SDK 2.0.0 + uvicorn + starlette
- **依存**: 標準ライブラリのみ（既存コード）+ mcp/uvicorn/starlette（MCP サーバ用）

### tools (5)

1. `render_table` — JSON rows → CJK 揃い AA テーブル
2. `measure_width` — 表示幅 + grapheme クラスタ数
3. `mmd2ge` — Mermaid → Graph::Easy 形式
4. `fix_width` — 既存 AA の CJK 幅ずれ修正
5. `list_styles` — 枠線スタイル一覧

### resources (4)

- `aatable://spec` — 能力一覧 (JSON)
- `aatable://guide` — 使い方ガイド (Markdown)
- `aatable://styles` — スタイル一覧 (JSON)
- `skill://ambiguous-calibration` — Ambiguous 幅キャリブレーション手順 (Markdown)

### テスト結果

```
48 passed in 11.14s
```

既存 37 テスト + MCP e2e 11 テスト、全て通過。

## 協調 (issue-hub)

不要。他リポジトリの MCP 入口に依存しない。Graph::Easy は外部 Perl モジュールであり、MCP 協調対象外。

## 未決事項

なし。survey の open_questions は全て DESIGN.md で解決済み:
- `measure_width` は独立 tool とした（他サービスから再利用可能）
- `ambiguous_width` のデフォルトは 1（必須パラメータにはしない）
- 既存 services.json の aatable エントリ（cli）を MCP 対応に更新する

## 持ち主への質問

なし。持ち主は 2026-08-22 に deploy まで進めてよいと了承済み。

## 次のステップ

1. commit & push
2. `volta__svc_add(manifest)` dry-run → 確認 → `confirm: true`
3. prod で git clone/pull + `systemctl --user enable --now aatable`
4. `curl http://127.0.0.1:9251/healthz` が 200 になることを確認
5. `volta__gateway_routes_diff()` → 自分の 1 件のみ → `confirm: true`
6. `https://aatable.unlaxer.org/healthz` 200 確認
7. `catalog__backend_status` で `aatable` namespace が `ready` 確認
