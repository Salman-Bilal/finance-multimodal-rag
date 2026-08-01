"""
services/rag.py
─────────────────────
Hybrid Query Understanding RAG Engine with Automatic Fallback.
1. Structured Branch: Uses Groq LLM to extract payload metadata filters (e.g., product_id, sales_rep).
2. Semantic Branch: Converts user query into a 384-dim embedding.
3. Hybrid Qdrant Query: Tries strict metadata filtering first; automatically falls back 
   to room-scoped vector search if 0 exact payload matches are found.
"""
import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from groq import Groq
from qdrant_client.http import models as qdrant_models

from services.embedder import qdrant_client, COLLECTION_NAME, get_embedding

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ── 1. Structured Query Pydantic Schema ──────────────────────────────────────
class ExtractedEntities(BaseModel):
    product_id: Optional[str] = Field(None, description="Extracted Product ID or Order ID if mentioned")
    sales_rep: Optional[str] = Field(None, description="Extracted Sales Representative name if mentioned")
    file_type: Optional[str] = Field(None, description="Extracted file type e.g., pdf, csv if mentioned")


# ── 2. Query Understanding Layer ──────────────────────────────────────────────
def extract_query_entities(query: str) -> ExtractedEntities:
    """
    Structured Query Branch: Uses LLM Tool Calling / JSON mode to extract
    exact metadata fields from user natural language query.
    """
    if not groq_client:
        return ExtractedEntities()

    system_prompt = (
        "You are an entity extraction and query expansion assistant. "
        "Analyze the query and return: "
        "1. Extracted metadata (product_id, sales_rep, file_type) "
        "2. Synonyms/variations of key metrics (e.g., 'revenue' -> ['revenue', 'sales', 'turnover', 'income'])"
    )

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        content = json.loads(response.choices[0].message.content)
        return ExtractedEntities(**content)
    except Exception as e:
        print(f"⚠️ [ENTITY FALLBACK] Extraction failed: {e}")
        return ExtractedEntities()


# ── 3. Qdrant Payload Filter Construction ────────────────────────────────────
def build_qdrant_filter(room_id: int, entities: ExtractedEntities) -> qdrant_models.Filter:
    """
    Combines room scoping with structured metadata payload filters.
    """
    must_conditions: List[qdrant_models.FieldCondition] = [
        qdrant_models.FieldCondition(
            key="room_id",
            match=qdrant_models.MatchValue(value=room_id)
        )
    ]

    # Attach metadata filters if present
    if entities.product_id:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="product_id",
                match=qdrant_models.MatchValue(value=entities.product_id)
            )
        )

    if entities.sales_rep:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="sales_rep",
                match=qdrant_models.MatchValue(value=entities.sales_rep)
            )
        )

    if entities.file_type:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="file_type",
                match=qdrant_models.MatchValue(value=entities.file_type.lower())
            )
        )

    return qdrant_models.Filter(must=must_conditions)


# ── 4. Main Hybrid RAG Execution Pipeline ─────────────────────────────────────
def answer_question_with_hybrid_rag(
    query: str,
    room_id: int,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    top_k: int = 15,  # ⚡ Increased to 15 for better context coverage
    db: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Executes end-to-end Hybrid RAG: Entity Extraction + Vector Similarity + Fallback + LLM Generation.
    """
    print(f"\n🔍 [QUERY UNDERSTANDING] Processing query: '{query}'")

    # --- Step A: Structured Branch (Extract Entities) ---
    entities = extract_query_entities(query)
    print(f"🏷️ [STRUCTURED BRANCH] Extracted Entities: {entities.model_dump()}")

    # --- Step B: Semantic Branch (Dense Embedding) ---
    query_vector = get_embedding(query)
    print("🔢 [SEMANTIC BRANCH] Generated 384-dim query embedding vector.")

    # --- Step C: Qdrant Search with Hybrid Filtering ---
    qdrant_filter = build_qdrant_filter(room_id, entities)
    
    search_response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=qdrant_filter,
        limit=top_k
    )
    search_results = search_response.points

    # ⚡ AUTOMATIC FALLBACK: If strict metadata filtering returns 0 chunks, retry with room-scoped semantic search
    if not search_results and (entities.product_id or entities.sales_rep or entities.file_type):
        print("⚠️ [RETRIEVAL FALLBACK] Payload filter matched 0 chunks. Retrying with room-scoped semantic search...")
        room_only_filter = qdrant_models.Filter(
            must=[qdrant_models.FieldCondition(key="room_id", match=qdrant_models.MatchValue(value=room_id))]
        )
        search_response = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=room_only_filter,
            limit=top_k
        )
        search_results = search_response.points

    print(f"📥 [RETRIEVAL] Found {len(search_results)} relevant chunk(s) in Qdrant.")

    # Extract retrieved context & sources
    retrieved_chunks = []
    sources = []

    for point in search_results:
        payload = point.payload or {}
        content = payload.get("content", "")
        retrieved_chunks.append(content)
        
        # ⚡ Safe excerpt added for Streamlit frontend rendering
        sources.append({
            "filename": payload.get("filename", "Unknown"),
            "file_type": payload.get("file_type", "Unknown"),
            "chunk_index": payload.get("chunk_index", 0),
            "score": round(point.score, 4),
            "excerpt": content[:150] + "..." if len(content) > 150 else content
        })

    # --- Groundedness Guardrail ---
    if not retrieved_chunks:
        return {
            "answer": "I don't know based on the documents provided in this workspace.",
            "sources": []
        }

    # --- Step D: LLM Generator ---
    context_str = "\n\n---\n\n".join(retrieved_chunks)
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert grounded assistant. Answer the user's question strictly "
                "using ONLY the provided Context below. If the answer cannot be deduced from "
                "the context, respond with 'I don't know'. Do not make up information.\n\n"
                f"=== RETRIEVED CONTEXT ===\n{context_str}"
            )
        }
    ]

    if conversation_history:
        messages.extend(conversation_history[-6:])

    messages.append({"role": "user", "content": query})

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1
    )

    final_answer = response.choices[0].message.content

    return {
        "answer": final_answer,
        "sources": sources,
        "extracted_entities": entities.model_dump()
    }


# ── Alias for backwards compatibility ──────────────────────────────────────────
ask = answer_question_with_hybrid_rag