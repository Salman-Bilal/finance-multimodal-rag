# Finance Multimodal RAG Platform

**Industry:** Financial Services & Investment Analysis  
**Stack:** FastAPI · Streamlit · Qdrant · Groq (LLaMA 3.3 70B) · SQLite · Sentence Transformers

---

## Problem Statement

Financial analysts and investment teams work with a wide variety of document types — earnings PDFs, Excel models, PowerPoint decks, audio transcripts, research images, and more. Traditional search tools are keyword-based and siloed; they can't reason across formats or answer nuanced questions grounded in a specific set of documents.

This platform solves that by providing a **Retrieval-Augmented Generation (RAG)** workspace where users can:

- Upload documents in **9 formats** (PDF, DOCX, XLSX, CSV, PPTX, TXT, MD, JSON, HTML) plus images and audio/video
- Have each document automatically **chunked, embedded, and indexed** into a per-room vector store (Qdrant)
- Ask natural-language questions and receive **grounded answers** citing the exact source chunks — the LLM cannot hallucinate outside the retrieved context
- Maintain **isolated workspaces** (rooms) per project or client, with full chat history and source traceability

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Streamlit Frontend (UI)                     │
│  Auth → Room Manager → File Uploader → Chat + Sources Panel │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (REST)
┌────────────────────────▼────────────────────────────────────┐
│                 FastAPI Backend                              │
│  /auth  /rooms  /upload  /chat                              │
│  JWT Auth · SQLAlchemy ORM · Pydantic Schemas               │
└──────┬────────────────────────────────────┬─────────────────┘
       │                                    │
┌──────▼──────────┐               ┌─────────▼──────────────┐
│   SQLite DB     │               │   Qdrant Vector Store  │
│  Users, Rooms   │               │   (persistent on-disk) │
│  Messages, Files│               │   all-MiniLM-L6-v2     │
└─────────────────┘               │   384-dim COSINE       │
                                  └───────────┬────────────┘
                                              │ top-5 chunks
                                  ┌───────────▼────────────┐
                                  │   Groq API             │
                                  │   llama-3.3-70b        │
                                  │   Grounded RAG Prompt  │
                                  └────────────────────────┘
```

---

## Features

| Feature | Details |
|---|---|
| **Multi-format ingestion** | PDF (chunked), DOCX, CSV, XLSX, PPTX, TXT, MD, JSON, HTML, PNG/JPG (OCR), MP3/MP4 (Whisper) |
| **Per-room isolation** | Each workspace room has its own Qdrant filter — documents never bleed across rooms |
| **Strict grounding** | LLM instructed to answer only from retrieved context; replies "I don't know" if not found |
| **Source citations** | Every assistant answer returns the filename, file type, chunk index, and a 150-char excerpt |
| **Chat history** | Last 3 turns (6 messages) included in each Groq call for conversational continuity |
| **JWT Authentication** | bcrypt password hashing, HS256 JWT tokens, OAuth2 password flow |
| **Persistent vectors** | Qdrant stored on disk (`./qdrant_storage`) — survives server restarts |

---

## Prerequisites

- Python **3.11+** (tested on 3.14)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and on `PATH` (required for image uploads)
- A [Groq API key](https://console.groq.com/) (free tier available)

---

## Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd "capstone project"

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install all dependencies
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root (copy the template below):

```env
# --- Required ---
SECRET_KEY=your_super_secret_jwt_key_min_32_chars
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# --- Optional (defaults shown) ---
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./sql_app.db
QDRANT_PATH=./qdrant_storage
API_BASE_URL=http://127.0.0.1:8000
```

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ Yes | Secret used to sign JWT tokens. Use a random 32+ char string. |
| `GROQ_API_KEY` | ✅ Yes | Your Groq API key for LLaMA 3.3 70B inference. |
| `ALGORITHM` | No | JWT signing algorithm. Default: `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token lifetime in minutes. Default: `60`. |
| `DATABASE_URL` | No | SQLAlchemy DB URL. Default: SQLite at `./sql_app.db`. |
| `QDRANT_PATH` | No | Local path for persistent Qdrant storage. Default: `./qdrant_storage`. |
| `API_BASE_URL` | No | Backend URL used by Streamlit. Default: `http://127.0.0.1:8000`. |

> **Security note:** Never commit your `.env` file. It is listed in `.gitignore` by default.

---

## Running the Application

You need **two terminals** running simultaneously.

**Terminal 1 — FastAPI backend:**
```bash
uvicorn main:app --reload
```
Backend will be available at: `http://127.0.0.1:8000`  
Interactive API docs: `http://127.0.0.1:8000/docs`

**Terminal 2 — Streamlit frontend:**
```bash
streamlit run streamlit_app.py
```
UI will open automatically at: `http://localhost:8501`

---

## Quick Demo

Follow these steps to see the full end-to-end flow:

**1. Register**
- Open `http://localhost:8501`
- Click the **Register** tab
- Fill in username, email, and password → click **Register Account**

**2. Login**
- Switch to the **Login** tab
- Enter your **email** and password → click **Log In**

**3. Create a Workspace Room**
- In the sidebar, expand **➕ Create New Room**
- Enter a room name (e.g. `Q2 Earnings Analysis`) → click **Create Room**

**4. Upload Documents**
- Select the new room from the dropdown
- Click **Browse files** and choose a PDF, XLSX, DOCX, PPTX, or any supported format
- Click **📤 Submit for Vectorization**
- Watch the **📊 Document Status** panel — the file status will change to 🟢 **Ready**

**5. Chat**
- Type a question in the chat input at the bottom of the page
- The assistant will answer using only content from your uploaded documents
- Expand the **📚 Sources** section under each answer to see exactly which chunks were used

**6. Clear History**
- Click **🗑️ Clear History** in the top-right to wipe the conversation for the current room

---

## Project Structure

```
capstone project/
├── main.py                      # FastAPI app entry point
├── streamlit_app.py             # Streamlit frontend
├── requirements.txt             # Pinned dependencies
├── .env                         # Environment variables (not committed)
│
├── db/
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # ORM models: User, ChatRoom, ChatMessage, UploadedFile
│   └── schemas.py               # Pydantic response schemas
│
├── routers/
│   ├── auth.py                  # POST /auth/register, POST /auth/login
│   ├── rooms.py                 # GET/POST /rooms, DELETE /rooms/{id}
│   ├── upload.py                # POST /upload/{room_id}, GET /upload/{room_id}/files
│   └── chat.py                  # POST /chat/{room_id}, GET/DELETE /chat/{room_id}/history
│
├── services/
│   ├── auth.py                  # JWT creation/validation, password hashing
│   ├── vector_store.py          # Qdrant client + SentenceTransformer embedder
│   └── ingestion/
│       ├── pdf.py               # pypdf extractor with 500-char chunking
│       ├── docx.py              # python-docx paragraph chunker
│       ├── csv_excel.py         # pandas CSV + Excel row-to-text
│       ├── text_md.py           # Plain text / Markdown sliding-window chunker
│       ├── pptx.py              # python-pptx slide text extractor
│       ├── image.py             # pytesseract OCR extractor
│       ├── audio_video.py       # faster-whisper transcription
│       └── json_html.py         # JSON flattener + HTML tag stripper
│
├── uploads/                     # Temporary file staging (auto-cleaned)
├── qdrant_storage/              # Persistent Qdrant vector index (auto-created)
├── sql_app.db                   # SQLite database (auto-created)
└── alembic/                     # Database migration scripts
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | ❌ | Register a new user |
| POST | `/auth/login` | ❌ | Login, returns JWT token |
| GET | `/rooms/` | ✅ | List all rooms for current user |
| POST | `/rooms/` | ✅ | Create a new room |
| DELETE | `/rooms/{room_id}` | ✅ | Delete a room (owner only) |
| POST | `/upload/{room_id}` | ✅ | Upload and vectorize a document |
| GET | `/upload/{room_id}/files` | ✅ | List files and their status |
| POST | `/chat/{room_id}` | ✅ | RAG query — returns answer + sources |
| GET | `/chat/{room_id}/history` | ✅ | Paginated chat history |
| DELETE | `/chat/{room_id}/history` | ✅ | Clear chat history (owner only) |

---

## Supported File Formats

| Format | Extension | Extraction Method |
|---|---|---|
| PDF | `.pdf` | pypdf + 500-char overlap chunking |
| Word | `.docx` | python-docx paragraph grouping |
| Excel | `.xlsx` | pandas `read_excel` row-to-text |
| CSV | `.csv` | pandas `read_csv` row-to-text |
| PowerPoint | `.pptx` | python-pptx per-slide text |
| Plain Text | `.txt` | Sliding window chunker |
| Markdown | `.md` | Sliding window chunker |
| JSON | `.json` | Recursive key:value flattening |
| HTML | `.html` | Tag stripping + text chunking |
| Images | `.png`, `.jpg`, `.jpeg` | pytesseract OCR |
| Audio/Video | `.mp3`, `.wav`, `.mp4`, `.m4a` | faster-whisper (tiny model, CPU) |
