import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from groq import Groq
from qdrant_client.http import models as qdrant_models

from db.database import get_db
from db.models import ChatRoom, ChatMessage, User
from db.schemas import ChatQueryRequest, ChatResponse, ChatMessageResponse, SourceItem
from services.auth import get_current_user
from services.vector_store import qdrant_client, COLLECTION_NAME, get_embedding

router = APIRouter(prefix="/chat", tags=["Chat & RAG Engine"])

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


@router.post("/{room_id}", response_model=ChatResponse)
async def chat_with_room(
    room_id: int,
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG Chat endpoint:
    1. Verify room exists
    2. Retrieve top-5 chunks from Qdrant (filtered by room_id)
    3. Fetch last 6 turns of chat history
    4. Call Groq (llama-3.3-70b-versatile) with strict grounding prompt
    5. Store turns in ChatMessage table
    6. Return answer and sources
    """
    if not groq_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GROQ_API_KEY is not configured on the server."
        )

    # 1. Verify Room Exists
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat room not found.")

    user_query = request.query.strip()
    if not user_query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty.")

    # 2. Retrieve top-5 vector chunks from Qdrant filtered by room_id
    query_vector = get_embedding(user_query)
    
    query_response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="room_id",
                    match=qdrant_models.MatchValue(value=room_id)
                )
            ]
        ),
        limit=5
    )

    search_results = query_response.points

    # Extract source metadata and context text snippets
    context_blocks = []
    sources: List[SourceItem] = []

    for point in search_results:
        payload = point.payload or {}
        content = payload.get("content", "")
        if content:
            context_blocks.append(content)
            
            # Format source object with mandatory excerpt (first 150 chars)
            sources.append(SourceItem(
                filename=payload.get("filename", "unknown"),
                file_type=payload.get("file_type", "unknown"),
                chunk_index=payload.get("chunk_index", 0),
                excerpt=content[:150]
            ))

    # 3. Fetch last 6 prior message turns from database
    prior_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.room_id == room_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(6)
        .all()
    )
    prior_messages.reverse()  # Order chronologically

    # Assemble messages for Groq API
    messages_for_groq = []

    # Grounding System Prompt
    system_prompt = (
        "You are an expert financial and business AI assistant.\n"
        "STRICT GROUNDING RULE: Answer the user's question USING ONLY the provided context snippets below.\n"
        "If the answer cannot be determined strictly from the provided context snippets, reply EXACTLY with: 'I don't know'\n"
        "Do NOT use external general knowledge or make assumptions.\n\n"
        f"--- RETRIEVED CONTEXT FROM UPLOADED DOCUMENTS ---\n"
        + ("\n\n".join(context_blocks) if context_blocks else "No relevant document context found.")
    )

    messages_for_groq.append({"role": "system", "content": system_prompt})

    # Add historical turns
    for msg in prior_messages:
        messages_for_groq.append({"role": msg.role, "content": msg.content})

    # Add current user prompt
    messages_for_groq.append({"role": "user", "content": user_query})

    # 4. Call Groq API
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_for_groq,
            temperature=0.1,  # Low temperature for precise factual adherence
            max_tokens=1000
        )
        answer_text = completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Groq API Error: {str(e)}"
        )

    # If the model indicates it doesn't know / no context was found, reset sources to empty []
    if "i don't know" in answer_text.lower() or not context_blocks:
        sources = []

    # Convert sources to serializable list of dicts for SQL JSON storage
    sources_dict_list = [s.model_dump() for s in sources]

    # 5. Persist Chat Messages in SQLite DB
    user_msg_db = ChatMessage(
        room_id=room_id,
        user_id=current_user.id,
        role="user",
        content=user_query,
        sources=[]
    )
    assistant_msg_db = ChatMessage(
        room_id=room_id,
        user_id=current_user.id,
        role="assistant",
        content=answer_text,
        sources=sources_dict_list
    )

    db.add(user_msg_db)
    db.add(assistant_msg_db)
    db.commit()

    # 6. Return response
    return ChatResponse(
        answer=answer_text,
        sources=sources
    )

@router.get("/{room_id}/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    room_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all chat messages for a specific room ordered by creation date (paginated).
    """
    # Verify room exists
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat room not found.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.room_id == room_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return messages


@router.delete("/{room_id}/history", status_code=status.HTTP_200_OK)
async def clear_chat_history(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear all message history for a room (Owner authorization required).
    """
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat room not found.")

    # Authorization check: only room owner can clear history
    if room.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the room owner can clear chat history."
        )

    db.query(ChatMessage).filter(ChatMessage.room_id == room_id).delete()
    db.commit()

    return {"message": f"Chat history for room {room_id} has been cleared."}