# db/schemas.py
from pydantic import BaseModel
from typing import List, Optional
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
    sources: Optional[List[SourceItem]] = []
    created_at: datetime

    class Config:
        from_attributes = True