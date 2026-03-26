# 🧠 AI Knowledge System (Backend)

A FastAPI-based backend that enables users to upload documents, store knowledge, and query it using AI-powered Retrieval-Augmented Generation (RAG).

---

# 🚀 Features (Completed)

## 🧱 Core Backend

* FastAPI application (`main.py`)
* Modular architecture (api, ingestion, core)
* SQLAlchemy database integration
* Pydantic schemas for validation

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

## 🧩 Ingestion Pipeline (NEW 🔥)

Implemented full pipeline:

```
Upload → Extract → Clean → Chunk → Embed → Store
```

### Components:

* `uploader.py` → handles file uploads
* `extractor.py` → extracts text from files
* `chunker.py` → splits text into chunks

### Supported formats:

* PDF
* DOCX
* TXT

---

## 🔍 Embeddings

* Uses OpenAI / local embedding models
* Converts text chunks into vectors

---

## 🗄️ Vector Database

* ChromaDB integration
* Stores chunk embeddings
* Metadata stored:

  * document_id
  * workspace_id
  * chunk_index

---

## 🤖 RAG (Retrieval-Augmented Generation)

* Query embedding → similarity search
* Retrieves relevant chunks
* Passes context to LLM

---

## 💬 Chat / Query API

* Ask questions on uploaded data
* Returns context-aware answers

---

## 🧪 Tests

* Workspace tests
* Document tests
* Query tests

---

# 🧱 Project Structure

```
backend/
│
├── main.py
├── db.py
├── models.py
├── schemas.py
├── crud.py
├── embeddings.py
├── vector_store.py
├── rag.py
│
├── api/
│   ├── chat.py
│   ├── documents.py
│   ├── query.py
│   ├── upload.py
│   └── workspaces.py
│
├── ingestion/
│   ├── uploader.py
│   ├── extractor.py
│   └── chunker.py
│
├── core/
│   └── config.py
│
└── tests/
```

---

# ⚙️ Setup Instructions

## 1. Clone repository

```
git clone <repo-url>
cd backend
```

---

## 2. Create virtual environment

### Windows

```
python -m venv venv
venv\Scripts\activate
```

### Mac/Linux

```
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```
pip install -r requirements.txt
```

---

## 4. Set environment variables

Create `.env`:

```
OPENAI_API_KEY=your_key_here
```

---

## 5. Run server

```
uvicorn main:app --reload
```

---

# 🧪 Testing Modules

---

## 🟢 1. Workspace API

### Create workspace

```
POST /workspaces
```

Body:

```json
{
  "name": "Test Workspace"
}
```

---

### List workspaces

```
GET /workspaces
```

---

## 🟢 2. Document API (Text)

### Create document

```
POST /documents
```

Body:

```json
{
  "workspace_id": 1,
  "content": "This is a test document"
}
```

---

## 🟢 3. Document Upload API (FILE) 🔥

### Upload file

```
POST /documents/upload
```

Form-data:

```
workspace_id = 1
file = (PDF/DOCX/TXT)
```

---

### What happens internally:

```
File uploaded
→ Text extracted
→ Chunked (500–800 words)
→ Embedded
→ Stored in vector DB
```

---

## 🟢 4. Query API

### Ask question

```
POST /query
```

Body:

```json
{
  "workspace_id": 1,
  "query": "What is this document about?"
}
```

---

### Response:

```json
{
  "answer": "...",
  "sources": [...]
}
```

---

## 🟢 5. Chat API

```
POST /chat
```

* Multi-turn interaction
* Uses RAG internally

---

# 🔍 Debugging Tips

---

## Check stored chunks

```
vector_store.count()
```

---

## Print query results

Add debug:

```
print(vector_store.query(...))
```

---

## Check ingestion

Upload a file and verify:

* chunks created
* embeddings stored

---

# ⚠️ Known Limitations

* No authentication (yet)
* No streaming responses
* Basic chunking (not semantic)
* No reranking
* No frontend

---

# 🚀 Next Improvements

---

## 🔥 High Priority

* Workspace filtering in vector DB queries
* Better chunking (semantic)
* Prompt engineering

---

## ⚡ Medium

* Chat memory
* Streaming responses
* File preview

---

## 🧠 Advanced

* Hybrid search (BM25 + vector)
* Reranking
* Agent-based reasoning

---

# 💡 System Architecture

```
User
 ↓
FastAPI
 ↓
Upload API
 ↓
Ingestion Pipeline
 ↓
Vector DB (Chroma)
 ↓
RAG
 ↓
LLM
 ↓
Response
```

---

# 🧠 Summary

This backend enables:

✔ Upload documents
✔ Convert them into AI-understandable format
✔ Store knowledge efficiently
✔ Ask questions over private data

---

# 🏁 Final Vision

This system acts like:

```
Your own private ChatGPT trained on your documents
```

---
