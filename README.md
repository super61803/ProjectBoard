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

## Day-2 scope

- Project members and issue assignees
- Comments on issues

## Day-3 scope

- Project keys and sequential issue keys
- Labels on issues
- Issue list filters by status, priority, assignee, label, and title

## Day-4 scope

- Sprints with planned, active, and completed states
- Assign issues to a sprint
- Sprint board grouped by issue status

## Day-5 scope

- Link issues with blocks, relates, and duplicates
- Show those links on an issue
- Filter the issue list to blocked work
