from pypdf import PdfReader

def extract_pdf_chunks(file_path: str) -> list[str]:
    reader = PdfReader(file_path)
    chunks = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            chunks.append(text.strip())
    return chunks