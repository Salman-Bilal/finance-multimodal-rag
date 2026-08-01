
import docx 

def table_to_markdown(table) -> str:
    rows_data = []
    for row in table.rows:
        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        if any(row_cells):
            rows_data.append(" | ".join(row_cells))
            
    if not rows_data:
        return ""
    
    header = rows_data[0]
    separator = " | ".join(["---"] * len(table.columns))
    body = "\n".join(rows_data[1:])
    return f"{header}\n{separator}\n{body}"

def extract_docx_chunks(file_path: str, max_chunk_size: int = 500) -> list[str]:
    doc = docx.Document(file_path)
    elements = []

    for element in doc.element.body:
        if element.tag.endswith('p'):
            text = element.text.strip()
            if text:
                elements.append(text)
        elif element.tag.endswith('tbl'):
            table = docx.table.Table(element, doc)
            md_table = table_to_markdown(table)
            if md_table:
                elements.append(md_table)

    chunks, current_chunk = [], ""
    for el in elements:
        if len(current_chunk) + len(el) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = el
        else:
            current_chunk += f"\n\n{el}" if current_chunk else el
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks