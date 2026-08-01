def extract_text_chunks(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    chunk_size = 500
    chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size - 50)]
    return [c.strip() for c in chunks if c.strip()]