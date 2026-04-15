# Pdf Merge Ai

> By [MEOK AI Labs](https://meok.ai) — PDF analysis, merge/split planning, and metadata extraction. By MEOK AI Labs.

PDF analysis, merge planning, split planning, and metadata extraction. — MEOK AI Labs.

## Installation

```bash
pip install pdf-merge-ai-mcp
```

## Usage

```bash
# Run standalone
python server.py

# Or via MCP
mcp install pdf-merge-ai-mcp
```

## Tools

### `merge_info`
Plan a PDF merge operation. Provide file descriptions as JSON array of objects with 'name', 'pages' (optional), and 'size_kb' (optional) fields.

**Parameters:**
- `file_descriptions` (str)
- `output_name` (str)

### `split_info`
Plan a PDF split operation. Split spec examples: 'every 5' (5-page chunks), '1-3,4-8,9-12' (custom ranges), 'even' / 'odd' (page parity).

**Parameters:**
- `source_name` (str)
- `total_pages` (int)
- `split_spec` (str)

### `get_metadata`
Extract or generate PDF metadata. Provide either base64-encoded first 1KB of PDF, or a JSON object with manual metadata fields.

**Parameters:**
- `pdf_base64_header` (str)
- `file_info_json` (str)

### `validate_pdf`
Validate PDF structure from base64-encoded header bytes. Checks version, structure, and encryption status.

**Parameters:**
- `pdf_base64_header` (str)


## Authentication

Free tier: 15 calls/day. Upgrade at [meok.ai/pricing](https://meok.ai/pricing) for unlimited access.

## Links

- **Website**: [meok.ai](https://meok.ai)
- **GitHub**: [CSOAI-ORG/pdf-merge-ai-mcp](https://github.com/CSOAI-ORG/pdf-merge-ai-mcp)
- **PyPI**: [pypi.org/project/pdf-merge-ai-mcp](https://pypi.org/project/pdf-merge-ai-mcp/)

## License

MIT — MEOK AI Labs
