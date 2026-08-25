#!/bin/bash
# aatable MCP server launcher
set -euo pipefail
cd /home/opa/aatable
exec python3 mcp/server.py
