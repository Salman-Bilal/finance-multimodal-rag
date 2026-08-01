# db/schemas.py
from pydantic import BaseModel
from typing import Any, List, Optional
from datetime import datetime


class SourceItem(BaseModel):
    filename: str
    file_type: str
    chunk_index: int
    excerpt: str


class ChatQueryRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem] = []


class ChatMessageResponse(BaseModel):
    id: int
    room_id: int
    user_id: int
    role: str
    content: str
    # List[Any] so history rows that contain old analytics meta dicts
    # ({"is_analytics": True, ...}) don't cause a ResponseValidationError.
    # New assistant messages will still have proper SourceItem dicts.
    sources: Optional[List[Any]] = []
    created_at: datetime

    class Config:
        from_attributes = True
