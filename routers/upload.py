import os
import uuid
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import UploadedFile, ChatRoom, User
from services.auth import get_current_user
from services.embedder import qdrant_client, COLLECTION_NAME, get_embeddings_batch
from qdrant_client.http.models import PointStruct

# Import extractors
from services.ingestion.pdf import extract_pdf_chunks
from services.ingestion.docx import extract_docx_chunks
from services.ingestion.csv_excel import extract_csv_chunks
from services.ingestion.text_md import extract_text_chunks
from services.ingestion.image import extract_image_chunks
from services.ingestion.audio_video import extract_audio_video_chunks
from services.ingestion.pptx import extract_pptx_chunks
from services.ingestion.json_html import extract_json_html_chunks

router = APIRouter(prefix="/upload", tags=["Ingestion"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class FileStatusResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    error_message: str | None = None

    class Config:
        from_attributes = True


def _get_owned_room(room_id: int, current_user: User, db: Session) -> ChatRoom:
    room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.owner_id == current_user.id
    ).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Room not found or you do not have permission to access it."
        )
    return room



@router.post("/{room_id}", status_code=status.HTTP_201_CREATED)
async def upload_file(
    room_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and vectorize a document into the specified room."""
    print(f"\n📥 [INGESTION] Received upload request for file: '{file.filename}' in Room ID: {room_id}")

    _get_owned_room(room_id, current_user, db)

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")

    db_file = UploadedFile(
        filename=file.filename,
        file_type=ext,
        file_path=None,
        room_id=room_id,
        status="processing"
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"💾 [FILE SAVED] Temporarily saved file to: {temp_path}")

        print(f"🔀 [ROUTING] Extracting content using extension format: '.{ext}'")
        if ext == "pdf":
            chunks = extract_pdf_chunks(temp_path)
        elif ext in ("doc", "docx"):
            chunks = extract_docx_chunks(temp_path)
        elif ext in ("csv", "xlsx"):
            chunks = extract_csv_chunks(temp_path)
        elif ext in ("txt", "md"):
            chunks = extract_text_chunks(temp_path)
        elif ext in ("pptx", "ppt"):
            chunks = extract_pptx_chunks(temp_path)
        elif ext in ("png", "jpg", "jpeg", "bmp"):
            chunks = extract_image_chunks(temp_path)
        elif ext in ("mp3", "wav", "mp4", "m4a", "avi"):
            chunks = extract_audio_video_chunks(temp_path)
        elif ext in ("json", "html"):
            chunks = extract_json_html_chunks(temp_path, ext)
        else:
            raise ValueError(f"Unsupported file type: .{ext}")

        print(f"✂️ [CHUNKING] Extracted {len(chunks)} text chunk(s) from '{file.filename}'")

        if not chunks:
            raise ValueError("No text content could be extracted from this file.")

        # ⚡ OPTIMIZED: Batch vector encoding for faster ingestion
        print("🔢 [EMBEDDINGS] Generating batch vector embeddings for chunks...")

        # CSV/XLSX extractor returns:
        # {
        #    "content": "...",
        #    "metadata": {...}
        # }
        #
        # Other extractors return:
        # "normal text chunk"

        if ext in ("csv", "xlsx"):
            embedding_texts = [
                chunk["content"]
                for chunk in chunks
            ]
        else:
            embedding_texts = chunks


        vectors = get_embeddings_batch(embedding_texts)


        points = []

        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):

            if ext in ("csv", "xlsx"):

                payload = {
                    "room_id": room_id,
                    "file_id": db_file.id,
                    "filename": file.filename,
                    "chunk_index": idx,
                    "file_type": ext,

                    # Store CSV columns separately
                    # Example:
                    # Product_ID:1001
                    # Sales_Rep:"Bob"
                    **chunk["metadata"],

                    # Store formatted text for semantic retrieval
                    "content": chunk["content"]
                }

            else:

                payload = {
                    "room_id": room_id,
                    "file_id": db_file.id,
                    "filename": file.filename,
                    "chunk_index": idx,
                    "file_type": ext,
                    "content": chunk
                }


            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload
                )
            )

        print(f"🗄️ [QDRANT] Upserting {len(points)} points to collection '{COLLECTION_NAME}'...")
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)

        db_file.status = "ready"
        db.commit()
        print(f"✅ [SUCCESS] File processing complete for ID {db_file.id}!\n")

        return {
            "file_id": db_file.id,
            "filename": file.filename,
            "chunks_created": len(chunks),
            "status": "ready"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ [ERROR] Ingestion failed: {str(e)}")
        db_file.status = "failed"
        db_file.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ingestion failed: {str(e)}"
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"🧹 [CLEANUP] Deleted temporary file at: {temp_path}")


# ---------------------------------------------------------------------------
# GET /upload/{room_id}/files — list all files + statuses for a room
# ---------------------------------------------------------------------------
@router.get("/{room_id}/files", response_model=List[FileStatusResponse])
def list_room_files(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return all uploaded files and their processing status for a room."""
    _get_owned_room(room_id, current_user, db)

    files = (
        db.query(UploadedFile)
        .filter(UploadedFile.room_id == room_id)
        .order_by(UploadedFile.uploaded_at.asc())
        .all()
    )
    return files


# ---------------------------------------------------------------------------
# GET /upload/debug/qdrant-payloads — developer inspection tool
# ---------------------------------------------------------------------------
@router.get("/debug/qdrant-payloads")
async def get_qdrant_payloads(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Retrieve vector payloads stored in Qdrant for manual inspection (authenticated)."""
    records, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        limit=limit,
        with_payload=True,
        with_vectors=False
    )
    return {
        "total_retrieved": len(records),
        "points": [point.payload for point in records]
    }