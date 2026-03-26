# Ai-Knowledge-System
ai-knowledge-system/
│
├── README.md
├── requirements.txt
├── .env
│
├── backend/
│   ├── main.py              # FastAPI app entrypoint
│   ├── db.py                # DB connection/session
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # All DB operations
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── workspaces.py    # workspace endpoints
│   │   ├── documents.py     # document upload + list
│   │   └── query.py         # search/query endpoint
│   │
│   └── core/
│       ├── __init__.py
│       └── config.py        # env variables (optional)
│
└── tests/
    ├── test_workspaces.py
    ├── test_documents.py
    └── test_query.py