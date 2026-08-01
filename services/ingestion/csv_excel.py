import pandas as pd
from services.embedder import format_row_for_embedding


def extract_csv_chunks(file_path: str) -> list[dict]:
    

    df = pd.read_csv(file_path)

    chunks = []

    for row in df.to_dict(orient="records"):

        content = format_row_for_embedding(row)

        chunks.append(
            {
                "content": content,
                "metadata": row
            }
        )

    return chunks