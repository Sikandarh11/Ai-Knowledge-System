# 🧠 Agentic AI Personal Knowledge System

A full-stack AI-powered personal knowledge assistant built with **FastAPI** (backend) and **React** (frontend). The system lets you upload documents, query them with RAG, manage emails intelligently, and handle scheduling through natural language — all powered by OpenAI and Google APIs.

---

# 🚀 Features

## 🧱 Core Backend

* FastAPI application with modular architecture
* SQLAlchemy + SQLite relational database
* Pydantic v2 schemas for validation
* Centralized YAML + env-var configuration (`core/config.py`, `core/settings.yml`)

---

## 📂 Workspaces

* Create and manage workspaces
* Logical isolation of knowledge
* Each workspace stores independent documents

---

## 📄 Document Management

* Create documents via text input
* Upload files (PDF, DOCX, TXT)
* Store full document content in relational DB

---

## 🧩 Ingestion Pipeline

Full automated pipeline:

```
Upload → Extract → Clean → Chunk → Embed → Store
```

### Components

| File | Role |
|------|------|
| `ingestion/uploader.py` | Validates file extension, saves to temp directory |
| `ingestion/extractor.py` | Extracts text from PDF (PyMuPDF), DOCX, or TXT |
| `ingestion/chunker.py` | Splits text into overlapping word-based chunks (500 words, 100-word overlap) |

### Supported formats

* PDF
* DOCX
* TXT

---

## 🔍 Embeddings

* Lazy-loaded embedding service (`embeddings.py`)
* Supports **OpenAI** (`text-embedding-3-small`) or **local SentenceTransformer** (`all-MiniLM-L6-v2`)
* Automatic fallback to local model if no OpenAI key is set

---

## 🗄️ Vector Database

* ChromaDB integration (`vector_store.py`)
* Cosine similarity search
* Persisted locally at `./chroma_db`
* Metadata per chunk: `document_id`, `workspace_id`, `chunk_index`, `filename`

---

## 🤖 RAG (Retrieval-Augmented Generation)

* Query embedding → top-5 similarity search → LLM generation (`rag.py`)
* Retrieves relevant chunks from ChromaDB
* Builds context-aware prompt and calls `gpt-4o-mini`
* Supports multi-turn conversation history (last 6 messages, max 4 000 chars)

---

## 💬 Chat / Query API

* Ask questions over uploaded documents
* Returns answer + source references (document ID, workspace ID, similarity distance)

---

## 📧 Email Agent (`agents/email_agent.py`) 🆕

LLM-powered email processing using `gpt-4o-mini`:

| Method | Description |
|--------|-------------|
| `summarize_email()` | 2-3 line summary of email content |
| `detect_intent()` | Classify as `URGENT` or `NORMAL` with reason |
| `generate_reply()` | Draft reply in requested tone (`formal` / `friendly` / `concise`) |
| `process_email()` | Run all three analyses in a single call |

---

## 📅 Scheduling Agent (`agents/scheduling_agent.py`) 🆕

Natural language scheduling assistant:

* Parses user requests into structured `ParsedQuery` (intent, date, time, duration, summary)
* Intents: `CHECK`, `CREATE`, `SUGGEST`, `UNKNOWN`
* Checks existing calendar events for conflicts
* Suggests up to 3 alternative meeting slots across 7 days
* Supports relative dates (`today`, `tomorrow`) and timezone conversion

---

## 🛠️ Services 🆕

### `services/email_service.py`
Orchestration layer for email operations:
* `process_email()` — validate → summarize → detect intent → generate reply
* `process_emails_bulk()` — batch processing with per-email error handling
* All methods return a standard envelope: `{"success": bool, "data": ..., "error": str|None}`

### `services/gmail_auth.py`
OAuth 2.0 authentication for the Gmail API:
* Loads existing token; refreshes silently when expired
* Launches browser OAuth flow for first-time auth
* Persists token for future runs; scope: `gmail.readonly`

### `services/google_calendar_service.py`
Google Calendar API client:
* `get_events()` — list upcoming events with optional query filter
* `create_event()` — create a new calendar event
* `delete_event()` — remove an event by ID

### `services/scheduler_service.py`
Core scheduling logic:
* `has_conflict()` — check if a time slot is already booked
* `find_free_slots()` — generate available slots within configured work hours
* `suggest_alternative()` — recommend 3 alternatives across 7 days

---

## 🔧 Tools 🆕

### `tools/email_tool.py`
Gmail tool layer:
* `fetch_emails()` — retrieve latest emails from inbox
* `parse_message()` — decode MIME, handle multipart, strip HTML
* Returns structured envelope with list of email dicts

### `tools/calendar_tool.py`
Google Calendar tool layer:
* `get_events()` / `create_event()` / `delete_event()`
* Returns structured event dicts with attendees and ISO-8601 start/end times

---

## 🖥️ Frontend (React + Vite) 🆕

A React 19 frontend with a dark neon design system:

* **Build tool**: Vite (ESM)
* **Routing**: React Router 7
* **Styling**: Tailwind CSS v4 with custom dark/neon theme
  * Dark palette: `dark-900` (#0a0a0f) → `dark-500`
  * Neon accents: `neon-purple`, `neon-blue`, `neon-cyan`, `neon-glow`
  * Custom utilities: `.text-glow`, `.neon-border`, `.card-gradient`, `.glass`
  * Fonts: Inter (UI), JetBrains Mono (code)

### Frontend scripts

```bash
npm run dev      # Vite dev server
npm run build    # Production bundle
npm run lint     # ESLint check
npm run preview  # Preview built app
```

---

# 🧱 Project Structure

```
Agentic-AI-Personal-Knowledge-System/
│
├── requirements.txt
│
├── backend/
│   ├── main.py              # FastAPI app, route registration, DB init
│   ├── db.py                # SQLite setup, SessionLocal
│   ├── models.py            # SQLAlchemy ORM: Workspace, Document
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # CRUD helpers
│   ├── embeddings.py        # EmbeddingService (OpenAI / SentenceTransformer)
│   ├── vector_store.py      # VectorStore (ChromaDB wrapper)
│   ├── rag.py               # RAGService (retrieve → prompt → generate)
│   │
│   ├── api/
│   │   ├── chat.py          # POST /chat  — RAG-powered Q&A
│   │   ├── documents.py     # CRUD + file upload for documents
│   │   ├── query.py         # POST /query — basic document search
│   │   ├── upload.py        # POST /upload — simple file upload
│   │   └── workspaces.py    # CRUD for workspaces
│   │
│   ├── ingestion/
│   │   ├── uploader.py      # File validation & temp storage
│   │   ├── extractor.py     # Text extraction (PDF/DOCX/TXT)
│   │   └── chunker.py       # Overlapping word-based chunking
│   │
│   ├── agents/
│   │   ├── email_agent.py       # Email summarise / triage / reply
│   │   └── scheduling_agent.py  # NL scheduling parser & conflict handler
│   │
│   ├── services/
│   │   ├── email_service.py             # Email orchestration layer
│   │   ├── gmail_auth.py                # Gmail OAuth 2.0 flow
│   │   ├── google_calendar_service.py   # Google Calendar API client
│   │   └── scheduler_service.py         # Conflict detection & slot finding
│   │
│   ├── tools/
│   │   ├── email_tool.py      # Gmail fetch/parse tool
│   │   └── calendar_tool.py   # Calendar get/create/delete tool
│   │
│   ├── utils/
│   │   └── extract_scheduling_info.py  # Scheduling metadata extraction helpers
│   │
│   └── core/
│       ├── config.py        # Settings loader (YAML + env-var overrides)
│       └── settings.yml     # App, DB, Google Calendar, scheduler config
│
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── eslint.config.js
    ├── package.json
    └── src/
        ├── main.jsx         # React entry point
        ├── App.jsx          # Root component
        └── index.css        # Tailwind v4 theme & custom utilities
```

---

# ⚙️ Setup Instructions

## 1. Clone repository

```bash
git clone <repo-url>
cd Agentic-AI-Personal-Knowledge-System
```

---

## 2. Backend setup

### Create virtual environment

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Set environment variables

Create a `.env` file (or export variables directly):

```
OPENAI_API_KEY=your_openai_key

# Optional — Google integrations
GOOGLE_CREDENTIALS_PATH=backend/core/secrets/credentials.json
GOOGLE_TOKEN_PATH=backend/core/secrets/token.json
GOOGLE_CALENDAR_ID=primary
```

You can also override any setting via `backend/core/settings.yml`.

### Run backend server

```bash
cd backend
uvicorn main:app --reload
```

---

## 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

---

## 4. Google API setup (optional — for Email & Calendar features)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Gmail API** and **Google Calendar API**
3. Create OAuth 2.0 credentials and download `credentials.json`
4. Place `credentials.json` in `backend/core/secrets/`
5. On first run, a browser window will open for OAuth consent; the token is saved automatically

---

# 🧪 API Reference

## 🟢 Workspace API

### Create workspace
```
POST /workspaces
```
```json
{ "name": "My Workspace" }
```

### List workspaces
```
GET /workspaces
```

### Delete workspace
```
DELETE /workspaces/{id}
```

---

## 🟢 Document API

### Create document (text)
```
POST /documents
```
```json
{ "workspace_id": 1, "content": "Document text here" }
```

### List documents
```
GET /documents?workspace_id=1
```

### Delete document
```
DELETE /documents/{id}
```

### Upload file (PDF / DOCX / TXT)
```
POST /documents/upload
```
Form-data:
```
workspace_id = 1
file = <your file>
```

**Internal flow:**
```
File → Validate → Extract text → Chunk → Embed → Store in vector DB
```

---

## 🟢 Chat API

```
POST /chat
```
```json
{
  "workspace_id": 1,
  "query": "What does this document say about X?",
  "history": [
    { "role": "user", "content": "Previous question" },
    { "role": "assistant", "content": "Previous answer" }
  ]
}
```

**Response:**
```json
{
  "answer": "Context-aware answer...",
  "sources": [
    { "document_id": 1, "workspace_id": 1, "distance": 0.23 }
  ]
}
```

---

## 🟢 Query API

```
POST /query
```
```json
{ "workspace_id": 1, "query": "search term" }
```

---

# 💡 System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      User / Frontend                     │
└────────────────────────┬─────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   FastAPI Backend   │
              │    (main.py + api/) │
              └──┬──────────────┬───┘
                 │              │
       ┌─────────▼──────┐  ┌───▼──────────────────┐
       │ Ingestion       │  │   RAG Pipeline        │
       │ • uploader      │  │   • embeddings.py     │
       │ • extractor     │  │   • vector_store.py   │
       │ • chunker       │  │   • rag.py            │
       └─────────┬───────┘  └───┬──────────────────┘
                 │              │
       ┌─────────▼──────┐  ┌───▼──────────────┐
       │  SQLite DB      │  │  ChromaDB        │
       │  (app.db)       │  │  (chroma_db/)    │
       └─────────────────┘  └──────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  Agentic Modules                          │
├───────────────┬──────────────────┬───────────────────────┤
│  Agents       │  Services        │  Tools                │
│  email_agent  │  email_service   │  email_tool           │
│  sched_agent  │  gmail_auth      │  calendar_tool        │
│               │  calendar_svc    │                       │
│               │  scheduler_svc   │                       │
├───────────────┴──────────────────┴───────────────────────┤
│  External APIs                                           │
│  • Gmail API (OAuth 2.0)                                 │
│  • Google Calendar API                                   │
│  • OpenAI API (gpt-4o-mini, text-embedding-3-small)      │
└──────────────────────────────────────────────────────────┘
```

---

# 🔍 Debugging Tips

### Check stored vector chunks
```python
vector_store.count()
```

### Inspect query results
```python
print(vector_store.query(embedding, n_results=5))
```

### Verify ingestion
Upload a file via `POST /documents/upload` and confirm:
* Chunks created in ChromaDB
* Document record created in SQLite

### Check scheduler config
Review `backend/core/settings.yml` for timezone, work hours, and slot duration.

---

# ⚠️ Known Limitations

* No authentication layer (yet)
* No streaming responses
* Basic word-based chunking (not semantic)
* No reranking of retrieved chunks
* Frontend UI is an early-stage skeleton
* Email / scheduling agents not yet exposed through REST API endpoints

---

# 🚀 Planned Improvements

## 🔥 High Priority
* REST API endpoints for email and scheduling agents
* Workspace-scoped vector DB filtering
* Semantic / sentence-aware chunking
* Authentication (JWT or OAuth)

## ⚡ Medium
* Streaming LLM responses
* Chat memory persistence
* File preview in frontend

## 🧠 Advanced
* Hybrid search (BM25 + vector)
* Result reranking
* Multi-agent orchestration
* Full frontend UI for all features

---

# 🧠 Summary

This system provides:

✔ Upload & index documents (PDF, DOCX, TXT)  
✔ Ask questions over private knowledge (RAG)  
✔ Intelligent email summarisation, triage, and reply drafting  
✔ Natural language meeting scheduling with conflict detection  
✔ Google Calendar & Gmail integration via OAuth 2.0  
✔ Modern React frontend with dark neon design  

---

# 🏁 Vision

```
Your own private AI assistant — trained on your documents,
managing your inbox, and scheduling your meetings.
```

