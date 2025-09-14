# Collaborative Document Editing API (FastAPI)

A FastAPI-based backend that provides:

- User registration & authentication (JWT / OAuth2 password flow)
- Document creation & retrieval
- Real‑time collaborative text editing via WebSockets
- Operational Transformation (OT)-style conflict resolution for concurrent edits
- Persistence of edits as immutable operations with versioning

---
## Table of Contents
1. Features
2. Tech Stack
3. Architecture Overview
4. Data Model
5. Operational Transformation (Conflict Handling)
6. API Authentication Flow
7. Environment & Configuration
8. Installation & Setup
9. Running the App
10. REST API Reference
11. WebSocket Protocol (Real‑Time Editing)
12. Example Flows
13. Development Notes & Tips
14. Future Improvements

---
## 1. Features
- JWT-based login (token returned from `/api/v1/auth/login`).
- Simple user model (email + hashed password + optional phone).
- Create documents and collaboratively edit contents.
- Versioned operations stored in the database with replay capability.
- WebSocket endpoint for real‑time editing using insert/delete primitive operations.
- Automatic transformation of incoming ops against concurrent ones to avoid divergence.

## 2. Tech Stack
| Layer | Technology |
|-------|------------|
| Framework | FastAPI |
| ASGI Server | Uvicorn |
| Auth | OAuth2 password grant + JWT (`python-jose`) |
| DB | PostgreSQL (via SQLAlchemy ORM) |
| Migrations (planned) | Alembic (dependency present) |
| Realtime | WebSockets (FastAPI) |
| Task Queue (present, unused in core flow) | Celery + Redis (listed in requirements) |

## 3. Architecture Overview
```
FastAPI App
 ├── /api/v1/routes
 │    ├── user.py          (User CRUD: create, get)
 │    ├── auth.py          (Login -> JWT issuance)
 │    ├── document.py      (Create doc, fetch doc, list ops)
 │    └── websocket.py     (Realtime collaboration endpoint /ws/{doc_id}?token=... )
 │
 ├── core/
 │    ├── config.py        (Environment-driven settings)
 │    ├── token.py         (JWT creation & verification)
 │    └── security.py      (Hash/verify password)
 │
 ├── db/
 │    ├── models/          (SQLAlchemy models: User, Document, Operation)
 │    ├── crud/            (Persistence helpers)
 │    ├── schemas/         (Pydantic request/response models)
 │    └── session.py       (Engine + SessionLocal)
 │
 ├── utils/
 │    ├── transformation.py (Operational transformation logic)
 │    ├── helper.py         (Apply transformed ops to content)
 │    └── websocket.py      (Connection manager)
 │
 └── main.py               (App creation + router inclusion + metadata.create_all)
```

## 4. Data Model
### User
- id (UUID string primary key)
- email (unique)
- password (hashed)
- phone_number (optional)
- created_at

### Document
- id (UUID string)
- title
- content (full text snapshot)
- version (monotonic integer increment)
- owner_id (FK -> users)
- created_at / updated_at

### Operation
Represents one atomic change applied to a document.
- id (int auto)
- document_id (FK)
- user_id (FK)
- base_version (document version the client thought it was editing)
- position (int index in text)
- insert_text (nullable) – inserted string
- delete_len (nullable/int) – number of chars removed starting at position
- applied_version (document version AFTER this op applied)
- created_at (timestamp)

## 5. Operational Transformation (Conflict Handling)
Incoming operations are transformed against any operations that have been applied after the client's `base_version`:
1. Server loads all ops with `applied_version > base_version`.
2. For each concurrent op, the incoming insert/delete is position-adjusted via transformation rules (see `utils/transformation.py`).
3. The transformed op is applied to the latest authoritative document content.
4. Document version increments; operation persisted with new `applied_version`.
5. Result is broadcast to other connected clients while sender receives an `ack`.

If a client's `base_version` mismatches the server version before transform, server responds with `sync_needed` including authoritative `content` + `version` so client can reconcile.

## 6. API Authentication Flow
1. Register a user via `POST /api/v1/users/`.
2. Login via `POST /api/v1/auth/login` (OAuth2 form: `username`=email, `password`).
3. Receive `{ access_token, token_type }`.
4. Pass token in:
   - REST: `Authorization: Bearer <token>`
   - WebSocket: query param `?token=<token>` when connecting to `/ws/{doc_id}`.

## 7. Environment & Configuration
Configuration uses `pydantic-settings` (`app/core/config.py`). Required vars in `.env`:
```
database_hostname=localhost
database_port=5432
database_username=postgres
database_password=postgres
database_name=collab_db
secret_key=CHANGE_ME_TO_RANDOM_32+_CHARS
algorithm=HS256
access_token_expire_minutes=60
```
Connection string composition presumably in `session.py` (not shown here). Format (SQLAlchemy 1.4):
```
postgresql+psycopg2://<user>:<password>@<host>:<port>/<database>
```

## 8. Installation & Setup
### Prerequisites
- Python 3.10+
- PostgreSQL running locally
- (Optional) Redis if you intend to enable Celery tasks later

### Steps
```bash
# 1. Clone repo
git clone <your-fork-or-origin>
cd collab_editor

# 2. Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # On Windows bash / Git Bash

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create the database (if not exists)
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE collab_db;"

# 5. Create .env
cp .env.example .env   # (Create manually if example not present, paste vars from section 7)

# 6. Run the server
uvicorn app.main:app --reload --port 8000
```
Visit: http://127.0.0.1:8000/docs for Swagger UI.

## 9. Running the App
Development (auto-reload):
```bash
uvicorn app.main:app --reload
```
Production (example, without process manager):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 10. REST API Reference
Base prefix: `/api/v1`

### Health / Root
`GET /` -> `{ "message": "Hello, World!" }` (no auth).

### Users
| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| POST | /api/v1/users/ | No | `{ email, password, phone_number? }` | `UserResponse` |
| GET | /api/v1/users/{user_id} | Yes (Bearer) | – | `UserResponse` |

Notes:
- Duplicate email returns 400.
- 404 if user not found.

### Auth
| Method | Path | Auth | Body Type | Fields | Response |
|--------|------|------|-----------|--------|----------|
| POST | /api/v1/auth/login | No | form-data (OAuth2PasswordRequestForm) | `username` (email), `password` | `{ access_token, token_type }` |

Errors: 403 for invalid credentials.

### Documents
| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| POST | /api/v1/docs/ | Yes | `{ title?, content? }` | New document object |
| GET | /api/v1/docs/{doc_id} | Yes | – | Document object |
| GET | /api/v1/docs/{doc_id}/ops | Yes | – | `List[OperationOut]` |

Errors:
- 404 if document or ops not found.

## 11. WebSocket Protocol (Real‑Time Editing)
Endpoint:
```
/ws/{doc_id}?token=<JWT>
```
Messages are JSON.

### Server -> Client Message Types
| type | When | Payload |
|------|------|---------|
| `init` | On successful connect | `{ content, version }` |
| `ack` | After your operation is applied | `{ op, updated_version }` |
| `op` | Operation from another user | `{ op, updated_version }` |
| `sync_needed` | Your base_version stale | `{ content, version }` |
| `error` | Invalid message / DB issue | `{ message }` |

### Client -> Server Operation Message
```json
{
  "position": <int>,
  "insert_text": "optional string or null",
  "delete_len": <int>,
  "base_version": <int>
}
```
Rules:
- If performing deletion, set `delete_len > 0`.
- For pure insertion set `insert_text` and `delete_len = 0`.
- Mixed (replace) can send both insert_text and delete_len > 0 at same position.
- Always send the last known document `version` as `base_version`.

### Example Sequence
1. Client connects, receives: `{ "type":"init", "content":"", "version":0 }`.
2. Client types "Hello": sends `{ position:0, insert_text:"Hello", delete_len:0, base_version:0 }`.
3. Server transforms (no concurrent), applies -> version=1; replies `ack` + broadcasts `op` to others.

## 12. Example Flows
### Create & Edit a Document
```bash
# Register
http POST :8000/api/v1/users/ email=user@example.com password=Secret123

# Login
http -f POST :8000/api/v1/auth/login username=user@example.com password=Secret123
# -> copy access_token

# Create Document
http POST :8000/api/v1/docs/ "Authorization:Bearer $TOKEN" title="Test Doc" content=""
# -> returns id (DOC_ID)

# Open WebSocket (using wscat or websocat)
wscat -c "ws://localhost:8000/ws/$DOC_ID?token=$TOKEN"
```
Send operations as you edit.

## 13. Development Notes & Tips
- `models.Base.metadata.create_all(bind=engine)` in `main.py` is fine for dev; prefer Alembic migrations for production schema changes.
- Consider indexing `operations(document_id, applied_version)` for replay queries.
- Secure secret_key with strong random string; never commit real secrets.
- Add rate limiting / throttling for WebSocket in production.
- Add persistence snapshotting if documents become large (periodically store full content).

## 14. Future Improvements
- Alembic migration scripts & versioned upgrades.
- Replace naive password handling with strong validation rules.
- Add refresh tokens & logout/blacklist.
- Pagination for operations list.
- Subscribe to presence (who is online) in WebSocket.
- Optimistic batching of keystrokes (reduce op volume).
- Add Celery tasks for heavy analytics / PDF export (pdfkit listed).
- Unit & integration tests.
- Add CORS configuration for frontend origins.

---
## Quick Start TL;DR
```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
psql -U postgres -c "CREATE DATABASE collab_db;"
cp .env.example .env  # populate vars
uvicorn app.main:app --reload
open http://127.0.0.1:8000/docs
```

---
Feel free to extend this README as the project evolves.
