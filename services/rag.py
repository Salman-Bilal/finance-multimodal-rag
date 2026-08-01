import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from groq import Groq
from qdrant_client.http import models as qdrant_models

from services.embedder import qdrant_client, COLLECTION_NAME, get_embedding

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

FULL_SCAN_KEYWORDS = [
    "list all", "range", "min", "max", "total", "summary", "overview", 
    "all product", "all sales", "entire document", "full report", "highest", "lowest"
]


class ExtractedEntities(BaseModel):
    product_id: Optional[str] = Field(None, description="Extracted Product ID or Order ID if mentioned")
    sales_rep: Optional[str] = Field(None, description="Extracted Sales Representative name if mentioned")
    file_type: Optional[str] = Field(None, description="Extracted file type e.g., pdf, csv if mentioned")


def extract_query_entities(query: str) -> ExtractedEntities:
    if not groq_client:
        return ExtractedEntities()

    system_prompt = (
        "You are an entity extraction assistant. Analyze the user's question and extract "
        "any explicit metadata identifiers present: product_id (or order_id), sales_rep, or file_type. "
        "Return the output in valid json format with keys: 'product_id', 'sales_rep', and 'file_type'. "
        "If a key is not present in the user query, set its value to null."
    )

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract entities in json format from: {query}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        content = json.loads(response.choices[0].message.content)
        
        if content.get("product_id"):
            content["product_id"] = str(content["product_id"]).strip(" .#")
            
        return ExtractedEntities(**content)
    except Exception as e:
        print(f"⚠️ [ENTITY FALLBACK] Extraction failed: {e}")
        return ExtractedEntities()


def build_qdrant_filter(room_id: int, entities: ExtractedEntities) -> qdrant_models.Filter:
    
    must_conditions: List[qdrant_models.FieldCondition] = [
        qdrant_models.FieldCondition(
            key="room_id",
            match=qdrant_models.MatchValue(value=room_id)
        )
    ]

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


def answer_question_with_hybrid_rag(
    query: str,
    room_id: int,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    top_k: int = 50,
    db: Optional[Any] = None
) -> Dict[str, Any]:
    
    print(f"\n🔍 [QUERY UNDERSTANDING] Processing query: '{query}'")

    if any(kw in query.lower() for kw in FULL_SCAN_KEYWORDS):
        top_k = 40
        print("🌐 [FULL DOCUMENT SCAN DETECTED] Scaled top_k to 40 chunks.")

    entities = extract_query_entities(query)
    print(f"🏷️ [STRUCTURED BRANCH] Extracted Entities: {entities.model_dump()}")

    query_vector = get_embedding(query)
    print("🔢 [SEMANTIC BRANCH] Generated 384-dim query embedding vector.")

    qdrant_filter = build_qdrant_filter(room_id, entities)
    
    search_response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=qdrant_filter,
        limit=top_k
    )
    search_results = search_response.points

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

    retrieved_chunks = []
    sources = []

    for point in search_results:
        payload = point.payload or {}
        content = payload.get("content", "")
        retrieved_chunks.append(content)
        
        sources.append({
            "filename": payload.get("filename", "Unknown"),
            "file_type": payload.get("file_type", "Unknown"),
            "chunk_index": payload.get("chunk_index", 0),
            "score": round(point.score, 4),
            "excerpt": content[:150] + "..." if len(content) > 150 else content
        })

    if not retrieved_chunks:
        return {
            "answer": "I don't know based on the documents provided in this workspace.",
            "sources": []
        }

    context_str = "\n\n---\n\n".join(retrieved_chunks)
    
    system_prompt = (
        "You are an expert grounded assistant. Answer the user's question strictly "
        "using ONLY the provided Context below. If the answer cannot be deduced from "
        "the context, respond with 'I don't know'. Do not make up information.\n\n"
        f"=== RETRIEVED CONTEXT ===\n{context_str}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history[-6:])
    messages.append({"role": "user", "content": query})

    if not groq_client:
        return {
            "answer": "Groq client is not initialized. Please check GROQ_API_KEY.",
            "sources": sources
        }

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


ask = answer_question_with_hybrid_rag