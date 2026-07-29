import os
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

# Load embedding model (384-dimensional dense vectors)
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
embedder = SentenceTransformer(EMBED_MODEL_NAME)
VECTOR_SIZE = 384
COLLECTION_NAME = "multimodal_rag_chunks"

# Initialize Qdrant in-memory client (or local file storage)
qdrant_client = QdrantClient(":memory:")

def init_qdrant_collection():
    """Ensure Qdrant collection exists with vector parameters."""
    collections = [c.name for c in qdrant_client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

# Initialize on startup
init_qdrant_collection()

def get_embedding(text: str) -> list[float]:
    """Generate dense vector embeddings using Sentence Transformers."""
    return embedder.encode(text).tolist()