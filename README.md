# ProjectBoard

Project management API built with **Python**, **FastAPI**, and **PostgreSQL**.

Track projects, user stories, and issues from a single backend.

## Stack

- FastAPI — HTTP API
- SQLAlchemy 2.x — ORM
- PostgreSQL — primary database
- Pydantic Settings — configuration

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Create a PostgreSQL database named `projectboard` (or update `DATABASE_URL` in `.env`).

## Run

```bash
uvicorn app.main:app --reload
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Day-1 scope

- App bootstrap and settings
- Project / story / issue data models
- CRUD API routes for the core entities
