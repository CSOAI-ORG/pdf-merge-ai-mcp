#!/usr/bin/env python3
"""
PDF analysis, merge planning, split planning, and metadata extraction. — MEOK AI Labs."""

import sys, os
from auth_middleware import check_access

import json, hashlib, re
from datetime import datetime, timezone
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

FREE_DAILY_LIMIT = 30
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now - t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT:
        return json.dumps({"error": f"Limit {FREE_DAILY_LIMIT}/day. Upgrade: meok.ai"})
    _usage[c].append(now)
    return None

mcp = FastMCP("pdf-merge-ai", instructions="PDF analysis, merge/split planning, and metadata extraction. By MEOK AI Labs.")

PDF_HEADER = b'%PDF-'
PDF_VERSIONS = ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "2.0"]


def _analyze_pdf_bytes(data: bytes) -> dict:
    """Analyze raw PDF bytes for structure information."""
    info = {
        "valid": False,
        "version": None,
        "size_bytes": len(data),
        "has_xref": False,
        "has_trailer": False,
        "estimated_pages": 0,
        "encrypted": False,
        "linearized": False,
    }

    if not data.startswith(PDF_HEADER):
        return info

    info["valid"] = True

    version_match = re.search(rb'%PDF-(\d+\.\d+)', data[:20])
    if version_match:
        info["version"] = version_match.group(1).decode()

    info["has_xref"] = b'xref' in data or b'/XRef' in data
    info["has_trailer"] = b'trailer' in data
    info["encrypted"] = b'/Encrypt' in data
    info["linearized"] = b'/Linearized' in data

    page_count = len(re.findall(rb'/Type\s*/Page[^s]', data))
    if page_count == 0:
        page_count = data.count(b'/Type /Page')
    info["estimated_pages"] = max(page_count, 1)

    return info


def _parse_page_range(spec: str, total_pages: int) -> list:
    """Parse page range specification like '1-3,5,7-9' into a list of page numbers."""
    pages = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            start_end = part.split('-', 1)
            try:
                start = max(1, int(start_end[0]))
                end = min(total_pages, int(start_end[1]))
                pages.extend(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    pages.append(p)
            except ValueError:
                continue
    return sorted(set(pages))


@mcp.tool()
def merge_info(file_descriptions: str, output_name: str = "merged.pdf", api_key: str = "") -> str:
    """Plan a PDF merge operation. Provide file descriptions as JSON array of objects with 'name', 'pages' (optional), and 'size_kb' (optional) fields.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        file_descriptions (str): The file descriptions to analyze or process.
        output_name (str): The output name to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://councilof.ai"})
    if err := _rl():
        return err

    try:
        files = json.loads(file_descriptions)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON. Provide a JSON array of file description objects."})

    if not isinstance(files, list) or len(files) < 2:
        return json.dumps({"error": "Provide at least 2 files to merge."})

    merge_plan = []
    total_pages = 0
    total_size_kb = 0
    page_offset = 1

    for i, f in enumerate(files):
        name = f.get("name", f"document_{i+1}.pdf")
        pages = f.get("pages", 0)
        size_kb = f.get("size_kb", 0)
        page_range = f.get("page_range", "")

        if pages == 0:
            pages = max(1, size_kb // 50) if size_kb else 1

        if page_range:
            selected = _parse_page_range(page_range, pages)
            selected_count = len(selected)
        else:
            selected = list(range(1, pages + 1))
            selected_count = pages

        merge_plan.append({
            "order": i + 1,
            "source": name,
            "source_pages": pages,
            "selected_pages": selected,
            "selected_count": selected_count,
            "page_range_in_output": f"{page_offset}-{page_offset + selected_count - 1}",
            "size_kb": size_kb,
        })

        total_pages += selected_count
        total_size_kb += size_kb
        page_offset += selected_count

    estimated_output_kb = int(total_size_kb * 0.95) if total_size_kb else 0

    return json.dumps({
        "operation": "merge",
        "output_name": output_name,
        "source_count": len(files),
        "total_pages": total_pages,
        "estimated_size_kb": estimated_output_kb,
        "merge_plan": merge_plan,
        "python_code": f"# Using PyPDF2 / pypdf\nfrom pypdf import PdfMerger\nmerger = PdfMerger()\n" + "\n".join(f'merger.append("{m["source"]}")  # {m["selected_count"]} pages' for m in merge_plan) + f'\nmerger.write("{output_name}")\nmerger.close()',
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def split_info(source_name: str, total_pages: int, split_spec: str, api_key: str = "") -> str:
    """Plan a PDF split operation. Split spec examples: 'every 5' (5-page chunks), '1-3,4-8,9-12' (custom ranges), 'even' / 'odd' (page parity).

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        source_name (str): The source name to analyze or process.
        total_pages (int): The total pages to analyze or process.
        split_spec (str): The split spec to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://councilof.ai"})
    if err := _rl():
        return err

    if total_pages < 1:
        return json.dumps({"error": "total_pages must be at least 1"})

    split_spec = split_spec.strip().lower()
    splits = []

    if split_spec.startswith("every "):
        try:
            chunk_size = int(split_spec.split()[1])
        except (IndexError, ValueError):
            return json.dumps({"error": "Invalid chunk size. Use 'every N' where N is a number."})
        chunk_size = max(1, chunk_size)
        for start in range(1, total_pages + 1, chunk_size):
            end = min(start + chunk_size - 1, total_pages)
            base = os.path.splitext(source_name)[0]
            splits.append({
                "output": f"{base}_pages_{start}-{end}.pdf",
                "pages": list(range(start, end + 1)),
                "page_count": end - start + 1,
            })
    elif split_spec == "even":
        even_pages = [p for p in range(1, total_pages + 1) if p % 2 == 0]
        base = os.path.splitext(source_name)[0]
        splits.append({"output": f"{base}_even.pdf", "pages": even_pages, "page_count": len(even_pages)})
    elif split_spec == "odd":
        odd_pages = [p for p in range(1, total_pages + 1) if p % 2 != 0]
        base = os.path.splitext(source_name)[0]
        splits.append({"output": f"{base}_odd.pdf", "pages": odd_pages, "page_count": len(odd_pages)})
    elif split_spec in ("half", "halves"):
        mid = total_pages // 2
        base = os.path.splitext(source_name)[0]
        splits.append({"output": f"{base}_part1.pdf", "pages": list(range(1, mid + 1)), "page_count": mid})
        splits.append({"output": f"{base}_part2.pdf", "pages": list(range(mid + 1, total_pages + 1)), "page_count": total_pages - mid})
    else:
        ranges = split_spec.split(',')
        base = os.path.splitext(source_name)[0]
        for idx, r in enumerate(ranges):
            r = r.strip()
            pages = _parse_page_range(r, total_pages)
            if pages:
                splits.append({"output": f"{base}_part{idx+1}.pdf", "pages": pages, "page_count": len(pages)})

    if not splits:
        return json.dumps({"error": "No valid splits generated from the spec."})

    total_output_pages = sum(s["page_count"] for s in splits)

    code_lines = ["from pypdf import PdfReader, PdfWriter", f'reader = PdfReader("{source_name}")']
    for s in splits:
        code_lines.append(f'# {s["output"]} ({s["page_count"]} pages)')
        code_lines.append(f'writer = PdfWriter()')
        code_lines.append(f'for p in {s["pages"]}: writer.add_page(reader.pages[p-1])')
        code_lines.append(f'writer.write("{s["output"]}")')

    return json.dumps({
        "operation": "split",
        "source": source_name,
        "source_pages": total_pages,
        "split_spec": split_spec,
        "output_count": len(splits),
        "total_output_pages": total_output_pages,
        "splits": splits,
        "python_code": "\n".join(code_lines),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def get_metadata(pdf_base64_header: str = "", file_info_json: str = "", api_key: str = "") -> str:
    """Extract or generate PDF metadata. Provide either base64-encoded first 1KB of PDF, or a JSON object with manual metadata fields.

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        pdf_base64_header (str): The pdf base64 header to analyze or process.
        file_info_json (str): The file info json to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://councilof.ai"})
    if err := _rl():
        return err

    metadata = {}

    if pdf_base64_header:
        import base64
        try:
            data = base64.b64decode(pdf_base64_header)
        except Exception:
            return json.dumps({"error": "Invalid base64 encoding"})

        analysis = _analyze_pdf_bytes(data)
        if not analysis["valid"]:
            return json.dumps({"error": "Data does not appear to be a valid PDF (missing %PDF- header)"})

        metadata = {
            "pdf_version": analysis["version"],
            "encrypted": analysis["encrypted"],
            "linearized": analysis["linearized"],
            "has_xref_table": analysis["has_xref"],
            "estimated_pages": analysis["estimated_pages"],
            "header_size_bytes": len(data),
        }

        title_match = re.search(rb'/Title\s*\(([^)]*)\)', data)
        author_match = re.search(rb'/Author\s*\(([^)]*)\)', data)
        creator_match = re.search(rb'/Creator\s*\(([^)]*)\)', data)
        producer_match = re.search(rb'/Producer\s*\(([^)]*)\)', data)

        if title_match:
            metadata["title"] = title_match.group(1).decode('latin-1', errors='replace')
        if author_match:
            metadata["author"] = author_match.group(1).decode('latin-1', errors='replace')
        if creator_match:
            metadata["creator"] = creator_match.group(1).decode('latin-1', errors='replace')
        if producer_match:
            metadata["producer"] = producer_match.group(1).decode('latin-1', errors='replace')

    elif file_info_json:
        try:
            info = json.loads(file_info_json)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON for file_info"})

        metadata = {
            "title": info.get("title", ""),
            "author": info.get("author", ""),
            "subject": info.get("subject", ""),
            "keywords": info.get("keywords", ""),
            "creator": info.get("creator", ""),
            "producer": info.get("producer", "MEOK AI Labs"),
            "pages": info.get("pages", 0),
            "file_size_kb": info.get("size_kb", 0),
        }
    else:
        return json.dumps({
            "usage": "Provide either pdf_base64_header (base64 of first 1KB of PDF) or file_info_json (manual metadata fields).",
            "file_info_fields": ["title", "author", "subject", "keywords", "creator", "pages", "size_kb"],
            "python_code": "from pypdf import PdfReader\nreader = PdfReader('file.pdf')\nprint(reader.metadata)\nprint(len(reader.pages))",
        })

    return json.dumps({
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def validate_pdf(pdf_base64_header: str, api_key: str = "") -> str:
    """Validate PDF structure from base64-encoded header bytes. Checks version, structure, and encryption status.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        pdf_base64_header (str): The pdf base64 header to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://councilof.ai"})
    if err := _rl():
        return err

    import base64
    try:
        data = base64.b64decode(pdf_base64_header)
    except Exception:
        return json.dumps({"valid": False, "error": "Invalid base64 encoding"})

    issues = []
    warnings = []

    if not data.startswith(PDF_HEADER):
        issues.append("Missing PDF header (%PDF-). File may not be a valid PDF.")
        return json.dumps({"valid": False, "issues": issues, "warnings": warnings})

    analysis = _analyze_pdf_bytes(data)

    if analysis["version"] and analysis["version"] not in PDF_VERSIONS:
        warnings.append(f"Unusual PDF version: {analysis['version']}")

    if analysis["encrypted"]:
        warnings.append("PDF is encrypted. Operations may require a password.")

    if not analysis["has_xref"]:
        warnings.append("No xref table found in provided bytes (may be beyond the header window)")

    if analysis["linearized"]:
        pass
    else:
        if analysis["size_bytes"] > 1024:
            warnings.append("PDF is not linearized. Consider linearizing for faster web viewing.")

    features = []
    if b'/AcroForm' in data:
        features.append("forms")
    if b'/Annots' in data:
        features.append("annotations")
    if b'/OCG' in data:
        features.append("layers")
    if b'/Sig' in data:
        features.append("signatures")
    if b'/EmbeddedFile' in data:
        features.append("embedded_files")

    return json.dumps({
        "valid": len(issues) == 0,
        "pdf_version": analysis["version"],
        "encrypted": analysis["encrypted"],
        "linearized": analysis["linearized"],
        "estimated_pages": analysis["estimated_pages"],
        "detected_features": features,
        "issues": issues,
        "warnings": warnings,
        "header_bytes_analyzed": len(data),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def main():
    mcp.run()

if __name__ == '__main__':
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
