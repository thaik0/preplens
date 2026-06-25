"""Simple character-based chunking for source notes."""


def chunk_text(
    text: str, chunk_size: int = 800, overlap: int = 150
) -> list[dict[str, int | str]]:
    """Split text into ordered chunks while preserving character offsets."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if overlap < 0:
        raise ValueError("overlap must be 0 or greater.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    chunks: list[dict[str, int | str]] = []
    start_char = 0

    while start_char < len(text):
        end_char = min(start_char + chunk_size, len(text))
        chunk = text[start_char:end_char]
        chunks.append(
            {
                "chunk_index": len(chunks),
                "text": chunk,
                "start_char": start_char,
                "end_char": end_char,
            }
        )

        if end_char == len(text):
            break

        start_char = end_char - overlap

    return chunks
