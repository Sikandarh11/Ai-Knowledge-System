# Workspace API

A lightweight FastAPI backend for managing **workspaces** and **documents**, with full-text search support. Built with SQLAlchemy ORM and SQLite.

---

## Project Structure

```
.
├── backend/
│   ├── __init__.py
│   ├── main.py          # App entry point, router registration, DB init
│   ├── db.py            # Engine, session, Base, get_db dependency
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── crud.py          # Database access functions
│   ├── api/
│   │   ├── __init__.py
│   │   ├── workspaces.py
│   │   ├── documents.py
│   │   └── query.py
│   └── core/
│       ├── __init__.py
│       └── config.py    # Environment-based settings
├── tests/
│   ├── __init__.py
│   ├── test_workspaces.py
│   ├── test_documents.py
│   └── test_query.py
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the development server

```bash
uvicorn backend.main:app --reload
```

The API will be available at: `http://127.0.0.1:8000`

Interactive docs: `http://127.0.0.1:8000/docs`

---

## Environment Variables

| Variable       | Default              | Description              |
|----------------|----------------------|--------------------------|
| `APP_NAME`     | `Workspace API`      | Application name         |
| `APP_VERSION`  | `1.0.0`              | Application version      |
| `DEBUG`        | `false`              | Enable debug mode        |
| `DATABASE_URL` | `sqlite:///./app.db` | SQLAlchemy database URL  |

---

## API Overview

### Health

| Method | Endpoint | Description     |
|--------|----------|-----------------|
| GET    | `/`      | Health check    |

### Workspaces

| Method | Endpoint               | Description              |
|--------|------------------------|--------------------------|
| POST   | `/workspaces`          | Create a new workspace   |
| GET    | `/workspaces`          | List all workspaces      |
| DELETE | `/workspaces/{id}`     | Delete workspace by ID   |

### Documents

| Method | Endpoint                             | Description                         |
|--------|--------------------------------------|-------------------------------------|
| POST   | `/documents`                         | Create a new document               |
| GET    | `/documents?workspace_id={id}`       | List documents for a workspace      |

### Query

| Method | Endpoint | Description                              |
|--------|----------|------------------------------------------|
| POST   | `/query` | Full-text search across document content |

---

## Example Requests

**Create a workspace**
```bash
curl -X POST http://localhost:8000/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "My Workspace"}'
```

**Create a document**
```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": 1, "content": "Hello world"}'
```

**Search documents**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "hello"}'
```

---

## Running Tests

```bash
pytest tests/
```