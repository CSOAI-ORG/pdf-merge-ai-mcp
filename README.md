<div align="center">

# Pdf Merge Ai MCP

**MCP server for pdf merge ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-pdf-merge-ai-mcp)](https://pypi.org/project/meok-pdf-merge-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Pdf Merge Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `merge_info` | Plan a PDF merge operation. Provide file descriptions as JSON array of objects w |
| `split_info` | Plan a PDF split operation. Split spec examples: 'every 5' (5-page chunks), '1-3 |
| `get_metadata` | Extract or generate PDF metadata. Provide either base64-encoded first 1KB of PDF |
| `validate_pdf` | Validate PDF structure from base64-encoded header bytes. Checks version, structu |

## Installation

```bash
pip install meok-pdf-merge-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pdf-merge-ai": {
      "command": "python",
      "args": ["-m", "meok_pdf_merge_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 4 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
