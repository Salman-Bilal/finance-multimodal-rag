from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ChatRoom, User
from services.auth import get_current_user

# Fix: redirect_slashes=True (default) means FastAPI will 307-redirect /rooms/ → /rooms,
# but Streamlit's requests library doesn't follow 307 with the same method for GET.
# Setting redirect_slashes=False on the router and registering BOTH paths is the safest fix.
router = APIRouter(prefix="/rooms", tags=["Rooms"])


class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RoomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int

    class Config:
        from_attributes = True


def _get_rooms(current_user: User, db: Session):
    return db.query(ChatRoom).filter(ChatRoom.owner_id == current_user.id).all()


# Register both /rooms and /rooms/ so the Streamlit call to /rooms/ always succeeds
@router.get("", response_model=List[RoomResponse])
@router.get("/", response_model=List[RoomResponse], include_in_schema=False)
def get_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return _get_rooms(current_user, db)


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_room(
    room_data: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_room = ChatRoom(
        name=room_data.name,
        description=room_data.description,
        owner_id=current_user.id
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


@router.delete("/{room_id}", status_code=status.HTTP_200_OK)
def delete_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.owner_id == current_user.id
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found or unauthorized")

    db.delete(room)
    db.commit()
    return {"message": "Room deleted successfully"}
