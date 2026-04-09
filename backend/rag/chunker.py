CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text or not text.strip():
        return []

    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(words):
        end = start + chunk_size
        chunk = words[start:end]
        if chunk:
            chunks.append(" ".join(chunk))
        if end >= len(words):
            break
        start += step

    return chunks
