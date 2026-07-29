import docx

def extract_docx_chunks(file_path: str) -> list[str]:
    doc = docx.Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    # Simple chunker: grouping paragraphs into ~500 character chunks
    chunks, current_chunk = [], ""
    for p in paragraphs:
        if len(current_chunk) + len(p) > 500:
            chunks.append(current_chunk)
            current_chunk = p
        else:
            current_chunk += f"\n{p}" if current_chunk else p
    if current_chunk:
        chunks.append(current_chunk)
    return chunks