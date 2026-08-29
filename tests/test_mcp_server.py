"""
E2E tests for AATable MCP server.

Starts the server as a subprocess, connects with MCP client, and verifies:
  healthz, tools/list, render_table, measure_width, mmd2ge, fix_width, list_styles, resources.
"""
import asyncio
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "mcp" / "server.py")],
        env={**__import__("os").environ, "PORT": str(port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    base_url = f"http://127.0.0.1:{port}"
    import urllib.request

    for _ in range(30):
        try:
            r = urllib.request.urlopen(f"{base_url}/healthz", timeout=1)
            if r.status == 200:
                break
        except Exception:
            time.sleep(0.3)
    else:
        out, err = proc.communicate(timeout=5)
        raise RuntimeError(f"server did not start\nstdout={out}\nstderr={err}")
    yield port
    proc.terminate()
    proc.wait(timeout=5)


def test_healthz(server):
    import urllib.request

    r = urllib.request.urlopen(f"http://127.0.0.1:{server}/healthz", timeout=2)
    data = json.loads(r.read())
    assert data["ok"] is True
    assert data["name"] == "aatable-mcp"
    assert "version" in data


@pytest.mark.asyncio
async def test_tools_list(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            names = {t.name for t in result.tools}
            assert "render_table" in names
            assert "measure_width" in names
            assert "mmd2ge" in names
            assert "fix_width" in names
            assert "list_styles" in names
            assert len(names) == 5


@pytest.mark.asyncio
async def test_render_table(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "render_table",
                {
                    "rows": [["名前", "得点"], ["田中太郎", "95"], ["佐藤", "88"]],
                    "style": "single",
                    "header": True,
                },
            )
            text = result.content[0].text if result.content else ""
            data = json.loads(text)
            assert "table" in data
            assert "田中太郎" in data["table"]
            assert "得点" in data["table"]
            lines = [l for l in data["table"].split("\n") if l]
            assert len(lines) >= 4


@pytest.mark.asyncio
async def test_render_table_emoji(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "render_table",
                {"rows": [["絵文字", "📝"], ["国旗", "🇯🇵"]], "header": True},
            )
            text = result.content[0].text if result.content else ""
            data = json.loads(text)
            import _aawidth

            lines = [l for l in data["table"].split("\n") if l]
            widths = [_aawidth.display_width(l) for l in lines]
            assert len(set(widths)) == 1, f"widths not uniform: {widths}"


@pytest.mark.asyncio
async def test_measure_width(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("measure_width", {"text": "漢字AB"})
            text = result.content[0].text if result.content else ""
            data = json.loads(text)
            assert data["display_width"] == 6
            assert data["grapheme_clusters"] == 4


@pytest.mark.asyncio
async def test_measure_width_emoji(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("measure_width", {"text": "😀"})
            text = result.content[0].text if result.content else ""
            data = json.loads(text)
            assert data["display_width"] == 2


@pytest.mark.asyncio
async def test_mmd2ge(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "mmd2ge",
                {"mermaid": "graph LR\nA[Start] --> B[End]"},
            )
            text = result.content[0].text if result.content else ""
            data = json.loads(text)
            assert "graph_easy" in data
            assert "Start" in data["graph_easy"]
            assert "End" in data["graph_easy"]
            assert "-->" in data["graph_easy"]


@pytest.mark.asyncio
async def test_fix_width(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "fix_width",
                {"text": "+-----+\n|漢字|\n+-----+"},
            )
            text = result.content[0].text if result.content else ""
            data = json.loads(text)
            assert "fixed" in data
            assert isinstance(data["fixed"], str)


@pytest.mark.asyncio
async def test_list_styles(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("list_styles", {})
            text = result.content[0].text if result.content else ""
            data = json.loads(text)
            assert len(data["styles"]) == 5
            names = {s["name"] for s in data["styles"]}
            assert names == {"single", "double", "bold", "ascii", "round"}


@pytest.mark.asyncio
async def test_resource_spec(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.read_resource("aatable://spec")
            content = result.contents[0]
            data = json.loads(content.text)
            assert data["namespace"] == "aatable"
            assert "capabilities" in data
            assert len(data["capabilities"]) >= 5


@pytest.mark.asyncio
async def test_resource_guide(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.read_resource("aatable://guide")
            content = result.contents[0]
            assert "AATable" in content.text
            assert "render_table" in content.text


@pytest.mark.asyncio
async def test_render_table_rejects_huge_padding(server):
    """padding=1e9 would allocate ~GB strings; must be rejected."""
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "render_table",
                {"rows": [["a", "b"]], "padding": 1_000_000_000},
            )
            assert result.is_error is True
            text = result.content[0].text if result.content else ""
            assert "padding" in text


@pytest.mark.asyncio
async def test_render_table_rejects_negative_padding(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "render_table",
                {"rows": [["a", "b"]], "padding": -1},
            )
            assert result.is_error is True


@pytest.mark.asyncio
async def test_render_table_rejects_invalid_ambiguous_width(server):
    """ambiguous_width=999 corrupts display_width globally; must be rejected."""
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "render_table",
                {"rows": [["a", "b"]], "ambiguous_width": 999},
            )
            assert result.is_error is True
            text = result.content[0].text if result.content else ""
            assert "ambiguous_width" in text


@pytest.mark.asyncio
async def test_measure_width_rejects_invalid_ambiguous_width(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "measure_width",
                {"text": "abc", "ambiguous_width": 0},
            )
            assert result.is_error is True


@pytest.mark.asyncio
async def test_fix_width_rejects_invalid_ambiguous_width(server):
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "fix_width",
                {"text": "+--+\n|a|\n+--+", "ambiguous_width": 3},
            )
            assert result.is_error is True


@pytest.mark.asyncio
async def test_render_table_accepts_boundary_padding(server):
    """padding=0 and padding=100 are valid boundary values."""
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for padding in (0, 100):
                result = await session.call_tool(
                    "render_table",
                    {"rows": [["a", "b"]], "padding": padding},
                )
                assert result.is_error is False
                text = result.content[0].text if result.content else ""
                data = json.loads(text)
                assert "table" in data


@pytest.mark.asyncio
async def test_invalid_ambiguous_width_does_not_pollute_global(server):
    """A rejected call must not leave the module global ambiguous_width mutated."""
    async with streamable_http_client(f"http://127.0.0.1:{server}/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Set a known good value first
            await session.call_tool(
                "measure_width", {"text": "x", "ambiguous_width": 1}
            )
            # Attempt to set an invalid value (should fail)
            bad = await session.call_tool(
                "measure_width", {"text": "x", "ambiguous_width": 999}
            )
            assert bad.is_error is True
            # Subsequent valid call must still work correctly
            result = await session.call_tool(
                "measure_width", {"text": "x", "ambiguous_width": 2}
            )
            assert result.is_error is False
