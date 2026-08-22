#!/usr/bin/env python3
"""
AATable MCP server — Streamable HTTP /mcp + /healthz.

Provides CJK-aware ASCII Art table rendering, display width measurement,
Mermaid→Graph::Easy conversion, and AA width fixing as MCP tools.

  python3 mcp/server.py          # starts on PORT env (default 9251)
  PORT=9300 python3 mcp/server.py

- MCPServer (mcp SDK 2.0.0) + Streamable HTTP /mcp
- /healthz via custom_route
- bind 0.0.0.0, PORT env
- All tools are pure functions (readOnlyHint: true)
- No confirm needed (no destructive operations)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aatable
import mmd2ge
import aafixwidth
import _aawidth as _aawidth_mod

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

MCP_VERSION = "0.1.0"
MCP_HOST = "0.0.0.0"
MCP_PORT = int(os.environ.get("PORT", "9251"))
MCP_PATH = "/mcp"


mcp = MCPServer(
    name="aatable",
    version=MCP_VERSION,
    description="CJK・絵文字対応 ASCII Art テーブル描画・幅計測・Mermaid→Graph::Easy 変換",
    instructions=(
        "AATable は Markdown/CSV/TSV を CJK・絵文字・Ambiguous 幅に対応した ASCII Art テーブルに変換する。"
        "render_table: JSON rows → AA テキスト。measure_width: 表示幅計測。"
        "mmd2ge: Mermaid → Graph::Easy 形式。fix_width: 既存 AA の CJK 幅ずれ修正。"
        "全 tool は純粋関数（副作用なし）。spec/guide は aatable://spec, aatable://guide を参照。"
    ),
)


@mcp.tool(
    description=(
        "JSON rows を CJK・絵文字対応の ASCII Art テーブルに変換する。"
        " 危険度: none（純粋関数）。"
        " rows は配列の配列（各行がセル文字列のリスト）。"
        " style: single/double/bold/ascii/round。"
        " ambiguous_width: 1(narrow, 既定) or 2(wide, macOS Terminal 等)。"
        " 出力: {table: string}"
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
def render_table(
    rows: list[list[str]],
    style: str = "single",
    padding: int = 1,
    align: str = "left",
    header: bool = True,
    ambiguous_width: int = 1,
) -> dict:
    _aawidth_mod.set_ambiguous_width(ambiguous_width)
    table = aatable.render_aa_table(
        rows,
        style_name=style,
        padding=padding,
        header=header,
        align=align,
    )
    return {"table": table}


@mcp.tool(
    description=(
        "文字列の表示幅（monospace 桁数）と grapheme クラスタ数を計測する。"
        " 危険度: none（純粋関数）。"
        " CJK 全角=2, 絵文字=2, Ambiguous=ambiguous_width 依存。"
        " 出力: {display_width: int, grapheme_clusters: int}"
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
def measure_width(text: str, ambiguous_width: int = 1) -> dict:
    _aawidth_mod.set_ambiguous_width(ambiguous_width)
    dw = aatable.display_width(text)
    gc = len(_aawidth_mod.split_grapheme_clusters(text))
    return {"display_width": dw, "grapheme_clusters": gc}


@mcp.tool(
    name="mmd2ge",
    description=(
        "Mermaid フローチャートを Graph::Easy 形式テキストに変換する。"
        " 危険度: none（純粋関数）。"
        " 出力は Graph::Easy 形式テキスト（boxart 化は別途 graph-easy コマンドが必要）。"
        " 出力: {graph_easy: string, direction: string}"
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
def mmd2ge_convert(mermaid: str) -> dict:
    lines = mermaid.splitlines()
    direction, ge_lines, _ = mmd2ge.parse_mermaid(lines)
    output_parts = []
    if direction != "down":
        output_parts.append(f"graph {{ flow: {direction}; }}")
    output_parts.append("\n".join(ge_lines))
    return {"graph_easy": "\n".join(output_parts), "direction": direction}


@mcp.tool(
    description=(
        "既存 ASCII Art の CJK 幅ずれを修正する。"
        " 危険度: none（純粋関数）。"
        " graph-easy が len() で幅計算するため CJK がずれるのを補正。"
        " 出力: {fixed: string}"
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
def fix_width(text: str, ambiguous_width: int = 1) -> dict:
    _aawidth_mod.set_ambiguous_width(ambiguous_width)
    fixed = aafixwidth.fix_aa_widths(text)
    return {"fixed": fixed}


@mcp.tool(
    description=(
        "サポートする枠線スタイル一覧を返す。"
        " 危険度: none（純粋関数）。"
        " 出力: {styles: [{name, sample}]}"
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
def list_styles() -> dict:
    sample_rows = [["名前", "値"], ["あいう", "123"]]
    styles = []
    for name in aatable.STYLES:
        sample = aatable.render_aa_table(sample_rows, style_name=name, padding=1)
        styles.append({"name": name, "sample": sample})
    return {"styles": styles}


# ---------- resources ----------

_GUIDE_MD = """\
# AATable MCP Guide

AATable は CJK・絵文字・Ambiguous 文字に対応した ASCII Art テーブル変換ツールです。

## Tools

### render_table
JSON rows（配列の配列）を ASCII Art テーブルに変換します。

入力例:
```json
{
  "rows": [["名前", "得点"], ["田中太郎", "95"], ["佐藤花子", "88"]],
  "style": "single",
  "padding": 1,
  "align": "left",
  "header": true,
  "ambiguous_width": 1
}
```

出力:
```json
{"table": "┌──────┬────┐\\n│名前  │得点│\\n├──────┼────┤\\n│田中太郎│95  │\\n├──────┼────┤\\n│佐藤花子│88  │\\n└──────┴────┘"}
```

### measure_width
文字列の表示幅（monospace 桁数）を計測します。CJK 全角=2、絵文字=2。

### mmd2ge
Mermaid フローチャートを Graph::Easy 形式テキストに変換します。
boxart 化には別途 `graph-easy` Perl モジュールが必要です。

### fix_width
graph-easy 等が生成した CJK 幅ずれの ASCII Art を修正します。

### list_styles
サポートする枠線スタイル（single/double/bold/ascii/round）の一覧とサンプルを返します。

## ambiguous_width

Ambiguous 文字（①②③, αβγ, ♠♥♦♣ 等）の表示幅はターミナル依存です。
- `1`（narrow, 既定）: Windows系、WSL
- `2`（wide）: macOS Terminal

各 tool の `ambiguous_width` パラメータで指定します。
キャリブレーションは `aacalibrate.py` で行えます（skill://ambiguous-calibration 参照）。

## 組み合わせ例

- `mstats__all_indicators` → `aatable__render_table`: 自治体統計を表で整形
- `jbench__rows` → `aatable__render_table`: 住所パーサ比較結果を一覧表に
"""

_SPEC_JSON = {
    "namespace": "aatable",
    "name": "AATable MCP",
    "version": MCP_VERSION,
    "summary": "CJK・絵文字対応 ASCII Art テーブル描画・幅計測・Mermaid→Graph::Easy 変換",
    "capabilities": [
        {"kind": "tool", "name": "render_table", "summary": "JSON rows → ASCII Art テーブル", "input": "rows: array<array<string>>, style, padding, align, header, ambiguous_width", "output": "{table: string}", "side_effect": "none", "long_running": False, "dry_run": False, "min_role": "VIEWER"},
        {"kind": "tool", "name": "measure_width", "summary": "文字列の表示幅計測", "input": "text: string, ambiguous_width", "output": "{display_width, grapheme_clusters}", "side_effect": "none", "long_running": False, "dry_run": False, "min_role": "VIEWER"},
        {"kind": "tool", "name": "mmd2ge", "summary": "Mermaid → Graph::Easy 変換", "input": "mermaid: string", "output": "{graph_easy, direction}", "side_effect": "none", "long_running": False, "dry_run": False, "min_role": "VIEWER"},
        {"kind": "tool", "name": "fix_width", "summary": "AA の CJK 幅ずれ修正", "input": "text: string, ambiguous_width", "output": "{fixed: string}", "side_effect": "none", "long_running": False, "dry_run": False, "min_role": "VIEWER"},
        {"kind": "tool", "name": "list_styles", "summary": "枠線スタイル一覧", "input": "なし", "output": "{styles: [{name, sample}]}", "side_effect": "none", "long_running": False, "dry_run": False, "min_role": "VIEWER"},
        {"kind": "resource", "name": "spec", "summary": "能力一覧", "input": "-", "output": "JSON", "side_effect": "none", "long_running": False, "dry_run": False, "min_role": "VIEWER"},
        {"kind": "resource", "name": "guide", "summary": "使い方ガイド", "input": "-", "output": "Markdown", "side_effect": "none", "long_running": False, "dry_run": False, "min_role": "VIEWER"},
        {"kind": "resource", "name": "styles", "summary": "スタイル一覧", "input": "-", "output": "JSON", "side_effect": "none", "long_running": False, "dry_run": False, "min_role": "VIEWER"},
    ],
    "compositions": [
        {"title": "DB 統計を表で整形", "flow": ["mstats__all_indicators", "aatable__render_table"], "note": "自治体統計の JSON rows を AA テーブルにしてチャットに貼る"},
        {"title": "住所パーサ比較結果の可視化", "flow": ["jbench__rows", "aatable__render_table"], "note": "パーサ比較結果を一覧表にしてレビュー"},
    ],
    "depends_on": [],
    "health": "/healthz",
    "docs": ["aatable://guide", "skill://ambiguous-calibration"],
}

_STYLES_JSON = {
    "styles": [
        {"name": name, "chars": chars}
        for name, chars in aatable.STYLES.items()
    ]
}

_SKILL_AMBIGUOUS = """\
# Ambiguous 文字幅のキャリブレーション

## いつ使う

Ambiguous 文字（①②③, αβγ, ♠♥♦♣, ☺ 等）の表示幅はターミナル依存です。
表のズレが Ambiguous 文字で起きているとき、`aacalibrate.py` で実機の幅を測定し、
プロファイルに保存できます。

## 手順

1. `python3 aacalibrate.py` をターミナルで実行（TTY 必須）
2. プローブが Ambiguous 文字の幅を測定（1 or 2）
3. `~/.aatable_profile.json` に保存される
4. `aatable.py` / `aafixwidth.py` は起動時にプロファイルを自動読み込み
5. MCP tool では `ambiguous_width` パラメータで明示指定可能

## 判断基準

- Windows系・WSL: 1 (narrow)
- macOS Terminal: 2 (wide)
- Linux 端末: 1 が多いが、フォント依存

## 注意

- `aacalibrate.py` はインタラクティブ TTY が必須。MCP tool には含めない。
- MCP 経由で呼ぶエージェントは `ambiguous_width` パラメータで明示する。
"""


@mcp.resource("aatable://spec", mime_type="application/json")
def spec_resource() -> str:
    """サーバの能力一覧（JSON）"""
    return json.dumps(_SPEC_JSON, ensure_ascii=False, indent=2)


@mcp.resource("aatable://guide", mime_type="text/markdown")
def guide_resource() -> str:
    """使い方ガイド（Markdown）"""
    return _GUIDE_MD


@mcp.resource("aatable://styles", mime_type="application/json")
def styles_resource() -> str:
    """サポートする枠線スタイル一覧（JSON）"""
    return json.dumps(_STYLES_JSON, ensure_ascii=False, indent=2)


@mcp.resource("skill://ambiguous-calibration", mime_type="text/markdown")
def skill_ambiguous_calibration() -> str:
    """Ambiguous 文字幅のキャリブレーション手順（SKILL.md 形式）"""
    return _SKILL_AMBIGUOUS


# ---------- /healthz ----------

@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"ok": True, "name": "aatable-mcp", "version": MCP_VERSION})


# ---------- main ----------

def main():
    import uvicorn
    app = mcp.streamable_http_app(
        streamable_http_path=MCP_PATH,
        stateless_http=False,
        host=MCP_HOST,
    )
    print(
        f"aatable MCP: http://{MCP_HOST}:{MCP_PORT}{MCP_PATH}  (healthz: /healthz)",
        file=sys.stderr,
    )
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT, log_level="warning")


if __name__ == "__main__":
    main()
