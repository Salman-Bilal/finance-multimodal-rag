from dotenv import load_dotenv
# Load .env BEFORE importing routers so all os.getenv() calls in
# services/auth.py, services/rag.py, services/embedder.py see the values.
load_dotenv()

from fastapi import FastAPI
from db.database import engine, Base
from routers import auth, rooms, upload, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Finance Multimodal RAG API",
    description="Backend API supporting Auth, Workspaces, Multimodal Uploads, and RAG Chat.",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(upload.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"message": "Finance & Investment Analysis RAG API is running."}
