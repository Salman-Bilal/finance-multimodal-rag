
import os
from typing import Any, Dict, List

import torch
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer



torch.set_num_threads(4)
torch.set_num_interop_threads(2)

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384

EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))

embedder = SentenceTransformer(
    EMBED_MODEL_NAME,
    device="cpu"
)

embedder.max_seq_length = 256



COLLECTION_NAME = "multimodal_rag_chunks"
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_storage")

qdrant_client = QdrantClient(path=QDRANT_PATH)


def _init_collection() -> None:
    """Create Qdrant collection if it doesn't exist."""

    collections = qdrant_client.get_collections().collections
    existing = {c.name for c in collections}

    if COLLECTION_NAME not in existing:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )


_init_collection()



def get_embedding(text: str) -> List[float]:

    if not text.strip():
        return [0.0] * VECTOR_SIZE

    embedding = embedder.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return embedding.tolist()


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
   
    if not texts:
        return []

    texts = [t if t.strip() else " " for t in texts]

    embeddings = embedder.encode(
        texts,
        batch_size=EMBED_BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )

    return embeddings.tolist()



def format_row_for_embedding(row_dict: Dict[str, Any]) -> str:
   

    return " | ".join(
        f"{key}: {value}"
        for key, value in row_dict.items()
        if value is not None and str(value).strip() != ""
    )