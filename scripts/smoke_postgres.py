"""Small live smoke check for the Docker Compose API/Postgres stack."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def fetch_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    try:
        health = fetch_json("/health")
        documents = fetch_json("/documents")
    except urllib.error.URLError as exc:
        print(f"Smoke check failed: API is not reachable: {exc}", file=sys.stderr)
        return 1

    if health != {"status": "ok", "app": "PrepLens"}:
        print(
            f"Smoke check failed: unexpected /health response: {health}",
            file=sys.stderr,
        )
        return 1

    if "documents" not in documents:
        print(
            f"Smoke check failed: /documents did not return documents: {documents}",
            file=sys.stderr,
        )
        return 1

    print("Smoke check passed: /health works and schema-backed /documents responds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
