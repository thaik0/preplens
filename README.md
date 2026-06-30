# PrepLens

PrepLens is a source-grounded interview prep assistant that helps users search their own study notes, retrieve relevant source chunks, generate cited answers, and collect feedback on retrieval quality.

I did this project because as I was prepping for interviews I would often ask ChatGPT/Claude questions about problems and would get frustrated with their hallucination. I'm sure you've experienced this; you ask something and it spits out something completely unrelated. This project is meant as a way to avoid that issue.

Right now its a local CLI backend MVP.

PrepLens is structured so CLI commands call reusable service-layer workflows in
`src/services/`, preparing the same application logic for a future API backend.

## What Works Now

- ingest `.md` and `.txt` study notes
- split notes into overlapping chunks
- store documents, chunks, embeddings, queries, answers, and feedback in SQLite
- search notes using keyword retrieval
- search notes using OpenAI embeddings and cosine similarity
- combine keyword and semantic search with hybrid retrieval
- generate citation-backed answers from retrieved chunks
- log query history, retrieved sources, generated answers, and citations
- collect source-level feedback such as `helpful`, `not_helpful`, and `wrong_source`
- use feedback from semantically similar past queries to rerank retrieval results
- evaluate retrieval quality using top-k recall and MRR

## Tech Stack

- Python
- SQLite
- SQLAlchemy Core for database access, with SQLite as the current default
  backend; Postgres support is planned.
- OpenAI API
- OpenAI embeddings
- NumPy
- JSON evaluation files
- CLI interface

## Depth

PrepLens is focused on the retrieval system around the LLM. It tracks which chunks were retrieved, which chunks were cited, whether users found those chunks helpful, and whether different retrieval methods actually find the right sources.

The current retrieval methods are:

- **Keyword search:** exact term matching baseline
- **Semantic search:** embedding-based search using cosine similarity
- **Hybrid search:** weighted combination of keyword and semantic scores
- **Feedback-aware search:** reranks hybrid candidates using feedback from semantically similar past queries

## Local Development

PrepLens currently runs as a local CLI tool.

Basic workflow:

```bash
python3 main.py ingest notes/
python3 main.py embed-chunks
python3 main.py ask "how do I detect a cycle in a linked list?"
python3 main.py eval-retrieval eval/questions.sample.json --include-feedback
```

OpenAI API access is required for embeddings and answer generation. API keys should be stored locally through environment variables and should not be committed.

### Local API

PrepLens also exposes a thin local FastAPI layer over the same service
workflows used by the CLI.

```bash
python3 -m uvicorn src.api.app:app --reload
```

Then visit:

http://127.0.0.1:8000/docs

### Docker

Docker is an optional way to run the local FastAPI API. Normal local
development does not require Docker.

Build the image:

```bash
docker build -t preplens .
```

Run the container, passing your OpenAI API key at runtime:

```bash
docker run -p 8000:8000 -e OPENAI_API_KEY="your_api_key" preplens
```

Then open:

http://127.0.0.1:8000/docs

Smoke test:

```bash
docker build -t preplens .
docker run -p 8000:8000 -e OPENAI_API_KEY="your_api_key" preplens
```

Visit http://127.0.0.1:8000/health or http://127.0.0.1:8000/docs.

The local `data/preplens.db` file is not baked into the Docker image. For now,
the container may create and use its own SQLite database; persistent
storage will be handled later with volumes or Postgres.

### Tests

```bash
python3 -m pytest
```

## Roadmap

Near-term:

- add more interview prep notes
- expand the hand-labeled eval set
- improve setup docs and examples
- add tests

Next architecture phase:

- add persistent Docker storage
- migrate to Postgres
- use cloud object storage for uploaded notes
- deploy the service
