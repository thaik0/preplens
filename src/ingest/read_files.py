"""File-reading utilities for supported local note formats."""

from pathlib import Path


SUPPORTED_EXTENSIONS = {".md", ".txt"}


def read_note_files(folder: str | Path) -> list[dict[str, str]]:
    """Read supported note files from a folder and return their text content."""
    folder_path = Path(folder)

    if not folder_path.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")
    if not folder_path.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {folder_path}")

    note_files: list[dict[str, str]] = []
    for path in sorted(folder_path.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        text = path.read_text(encoding="utf-8")
        note_files.append(
            {
                "filename": path.name,
                "filepath": str(path),
                "file_type": path.suffix.lower().lstrip("."),
                "text": text,
            }
        )

    return note_files
