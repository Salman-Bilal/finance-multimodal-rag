import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import UploadedFile, User
from services.auth import get_current_user
from services.vector_store import qdrant_client, COLLECTION_NAME, get_embedding
from qdrant_client.http.models import PointStruct

# Import extractors
from services.ingestion.pdf import extract_pdf_chunks
from services.ingestion.docx import extract_docx_chunks
from services.ingestion.csv_excel import extract_csv_chunks
from services.ingestion.text_md import extract_text_chunks
from services.ingestion.image import extract_image_chunks
from services.ingestion.audio_video import extract_audio_video_chunks
from services.ingestion.pptx import extract_pptx_chunks

router = APIRouter(prefix="/upload", tags=["Ingestion"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/{room_id}")
async def upload_file(
    room_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"\n📥 [INGESTION] Received upload request for file: '{file.filename}' in Room ID: {room_id}")
    
    # 1. Create file tracking record
    ext = file.filename.split(".")[-1].lower()
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    
    db_file = UploadedFile(
        filename=file.filename,
        file_type=ext,
        file_path=temp_path,
        room_id=room_id,
        status="processing"
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    try:
        # Save file to disk
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"💾 [FILE SAVED] Temporarily saved file to: {temp_path}")

        # 2. Route to correct extractor
        print(f"🔀 [ROUTING] Extracting content using extension format: '.{ext}'")
        if ext in ["pdf"]:
            chunks = extract_pdf_chunks(temp_path)
        elif ext in ["doc", "docx"]:
            chunks = extract_docx_chunks(temp_path)
        elif ext in ["csv", "xlsx"]:
            chunks = extract_csv_chunks(temp_path)
        elif ext in ["txt", "md"]:
            chunks = extract_text_chunks(temp_path)
        elif ext in ["pptx", "ppt"]:
            chunks = extract_pptx_chunks(temp_path)
        elif ext in ["png", "jpg", "jpeg", "bmp"]:
            chunks = extract_image_chunks(temp_path)
        elif ext in ["mp3", "wav", "mp4", "m4a", "avi"]:
            chunks = extract_audio_video_chunks(temp_path)
        else:
            raise ValueError(f"Unsupported file extension: .{ext}")

        print(f"✂️ [CHUNKING] Extracted {len(chunks)} text chunk(s) from '{file.filename}'")

        if not chunks:
            raise ValueError("No text content could be extracted from file.")

        # 3. Embed & Upsert to Qdrant
        print("🔢 [EMBEDDINGS] Generating vector embeddings for chunks...")
        points = []
        for idx, chunk in enumerate(chunks):
            vector = get_embedding(chunk)
            point_id = str(uuid.uuid4())
            
            # Payload schema requirement
            payload = {
                "room_id": room_id,
                "file_id": db_file.id,
                "filename": file.filename,
                "chunk_index": idx,
                "file_type": ext,
                "content": chunk
            }
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        print(f"🗄️ [QDRANT] Upserting {len(points)} points to collection '{COLLECTION_NAME}'...")
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)

        # 4. Mark status as ready
        db_file.status = "ready"
        db.commit()
        print(f"✅ [SUCCESS] File processing complete for ID {db_file.id}! Status set to 'ready'.\n")

        return {
            "file_id": db_file.id,
            "filename": file.filename,
            "chunks_created": len(chunks),
            "status": "ready"
        }

    except Exception as e:
        print(f"❌ [ERROR] Ingestion failed: {str(e)}")
        db_file.status = "failed"
        db_file.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ingestion failed: {str(e)}"
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)  # Clean up temp file
            print(f"🧹 [CLEANUP] Deleted temporary file at: {temp_path}")


@router.get("/debug/qdrant-payloads")
async def get_qdrant_payloads(limit: int = 10):
    """Retrieve vector payloads stored in Qdrant for manual inspection."""
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