import pandas as pd

def extract_csv_chunks(file_path: str) -> list[str]:
    df = pd.read_csv(file_path)
    # Convert rows to textual representations
    chunks = []
    for idx, row in df.iterrows():
        row_str = ", ".join([f"{col}: {val}" for col, val in row.items()])
        chunks.append(f"Row {idx + 1}: {row_str}")
    return chunks