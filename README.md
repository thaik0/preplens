# PrepLens

PrepLens is a source-grounded interview prep assistant for querying personal study notes with retrieved source citations and feedback. I built it because generic chat can drift away from the notes I actually trust; this keeps answers tied to my own prep material.

## What Works

- ingest local Markdown and text notes
- chunk and embed notes
- keyword, semantic, hybrid, and feedback-aware retrieval
- deterministic retrieval query normalization
- citation-backed answers from retrieved source chunks
- query, answer, source, citation, and feedback logging
- idempotent ingestion by source path
- FastAPI backend
- React/Vite demo frontend
- SQLite local mode
- Postgres through `DATABASE_URL`
- Docker Compose for API + Postgres
- SQLAlchemy Core database layer
- retrieval evals and tests

## Quick Start: Local SQLite

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your_key"

python3 main.py ingest notes/
python3 main.py embed-chunks
python3 -m uvicorn src.api.app:app --reload
```

Start the frontend in another shell:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The API docs are at:

```text
http://127.0.0.1:8000/docs
```

## Docker Compose: API + Postgres

```bash
export OPENAI_API_KEY="your_key"
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000/docs
```

Compose uses the local Postgres defaults in `docker-compose.yml`:

- database: `preplens`
- user: `preplens`
- password: `preplens`
- port: `5432`

Postgres data persists in the named Docker volume `preplens_postgres_data`.
The frontend is still run separately from `frontend/`.

## Useful CLI Commands

```bash
python3 main.py list-docs
python3 main.py ingest notes/
python3 main.py embed-chunks
python3 main.py hybrid-search "query"
python3 main.py feedback-search "query"
python3 main.py ask "query"
python3 main.py history
python3 main.py feedback-summary
python3 main.py eval-retrieval eval/questions.sample.json
```

## Tests

```bash
python3 -m pytest
```

## Current Limitations

- local/developer alpha
- no auth, users, or workspaces
- no hosted deployment yet
- no PDF ingestion yet
- no pgvector or vector database yet
- no Alembic migrations yet
- frontend is a demo flow, not a polished app
- source-grounded answers depend on the notes containing enough information

## Roadmap

- cleaner frontend flow
- document refresh or replace mode
- better retrieval eval set
- upload and PDF ingestion
- pgvector or another vector database path
- deployment, auth, and workspaces later
