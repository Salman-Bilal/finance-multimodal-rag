"""
routers/chat.py
────────────────
POST /chat/{room_id}         — RAG query (delegates entirely to services/rag.py)
GET  /chat/{room_id}/history  — paginated message history
DEL  /chat/{room_id}/history  — clear history (owner only)
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ChatRoom, ChatMessage, User
from db.schemas import ChatQueryRequest, ChatResponse, ChatMessageResponse, SourceItem
from services.auth import get_current_user
from services.rag import answer_question_with_hybrid_rag as ask

router = APIRouter(prefix="/chat", tags=["Chat & RAG Engine"])


# ---------------------------------------------------------------------------
# Ownership guard (shared by all three endpoints)
# ---------------------------------------------------------------------------
def _get_owned_room(room_id: int, current_user: User, db: Session) -> ChatRoom:
    room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.owner_id == current_user.id,
    ).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Room not found or you do not have permission to access it.",
        )
    return room


# ---------------------------------------------------------------------------
# POST /chat/{room_id}
# ---------------------------------------------------------------------------
@router.post("/{room_id}", response_model=ChatResponse)
async def chat_with_room(
    room_id: int,
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    RAG chat endpoint.
    Delegates retrieve → build_prompt → ask to services/rag.py.
    Persists both the user turn and the assistant turn in ChatMessage.
    """
    _get_owned_room(room_id, current_user, db)

    user_query = request.query.strip()
    if not user_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty.",
        )

    # Delegate the full RAG pipeline to services/rag.py
    try:
        # ⚡ FIX 1: Capture dict response cleanly from ask()
        rag_result = ask(query=user_query, room_id=room_id, db=db)
        answer_text = rag_result.get("answer", "")
        raw_sources = rag_result.get("sources", [])
    except RuntimeError as e:
        # Raised when GROQ_API_KEY is missing
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline error: {str(e)}",
        )

    # ⚡ FIX 2: Format sources safely for database persistence
    sources_dict = [
        s.model_dump() if hasattr(s, "model_dump") else s 
        for s in raw_sources
    ]

    # Persist both turns in SQLite
    db.add(ChatMessage(
        room_id=room_id,
        user_id=current_user.id,
        role="user",
        content=user_query,
        sources=[],
    ))
    db.add(ChatMessage(
        room_id=room_id,
        user_id=current_user.id,
        role="assistant",
        content=answer_text,
        sources=sources_dict,
    ))
    db.commit()

    return ChatResponse(answer=answer_text, sources=raw_sources)


# ---------------------------------------------------------------------------
# GET /chat/{room_id}/history
# ---------------------------------------------------------------------------
@router.get("/{room_id}/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    room_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all messages for a room ordered by creation time (paginated)."""
    _get_owned_room(room_id, current_user, db)

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.room_id == room_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return messages


# ---------------------------------------------------------------------------
# DELETE /chat/{room_id}/history
# ---------------------------------------------------------------------------
@router.delete("/{room_id}/history", status_code=status.HTTP_200_OK)
async def clear_chat_history(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear all message history for a room. Only the room owner can do this."""
    _get_owned_room(room_id, current_user, db)
    db.query(ChatMessage).filter(ChatMessage.room_id == room_id).delete()
    db.commit()
    return {"message": f"Chat history for room {room_id} has been cleared."}