import json
import re


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def extract_json_html_chunks(file_path: str, ext: str) -> list[str]:
    """
    Fix #5: Extract and chunk text from JSON and HTML files.
    - JSON: pretty-prints the structure as readable key:value text
    - HTML: strips all tags and extracts visible text
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    if ext == "json":
        try:
            data = json.loads(raw)
            # Flatten JSON into readable "key: value" lines
            lines = _flatten_json(data)
            text = "\n".join(lines)
        except json.JSONDecodeError:
            # Fallback: treat as plain text if malformed
            text = raw
    elif ext == "html":
        # Remove <script> and <style> blocks first
        text = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        # Strip all remaining HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
    else:
        text = raw

    if not text.strip():
        return [f"File '{file_path}' contained no extractable text content."]

    return _chunk_text(text)


def _flatten_json(obj, prefix: str = "") -> list[str]:
    """Recursively flatten a JSON object into readable key: value lines."""
    lines = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            lines.extend(_flatten_json(value, full_key))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            lines.extend(_flatten_json(item, f"{prefix}[{i}]"))
    else:
        lines.append(f"{prefix}: {obj}")
    return lines
