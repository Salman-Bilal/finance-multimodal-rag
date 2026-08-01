from pypdf import PdfReader


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def extract_pdf_chunks(file_path: str) -> list[str]:
    reader = PdfReader(file_path)
    chunks = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            page_chunks = _chunk_text(text.strip())
            chunks.extend(page_chunks)
    return chunks