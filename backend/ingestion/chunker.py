CHUNK_SIZE    = 500   # target words per chunk
CHUNK_OVERLAP = 100   # words shared between consecutive chunks


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping word-based chunks.

    Args:
        text:       Clean input string (output of extractor.py).
        chunk_size: Target number of words per chunk (default 500).
        overlap:    Number of words to repeat at the start of the next chunk (default 100).

    Returns:
        List of non-empty chunk strings. Returns [] if text is empty.
    """
    if not text or not text.strip():
        return []

    # ── 1. Tokenize into words ─────────────────────────────────────────────────
    words = text.split()

    if not words:
        return []

    # Edge case: text is shorter than one full chunk
    if len(words) <= chunk_size:
        return [" ".join(words)]

    # ── 2. Slide a window across the word list ─────────────────────────────────
    chunks = []
    start  = 0
    step   = chunk_size - overlap   # how far to advance after each chunk

    while start < len(words):
        end   = start + chunk_size
        chunk = words[start:end]

        # Only keep non-empty chunks
        if chunk:
            chunks.append(" ".join(chunk))

        # If this chunk already reached the end, stop
        if end >= len(words):
            break

        start += step

    return chunks
'''
---

**Visualising the sliding window:**
```
words:  [ w0  w1  w2 ... w499 | w500 ... w999 | ... ]

chunk 1:  start=0    end=500   → words[0:500]
chunk 2:  start=400  end=900   → words[400:900]  (100-word overlap with chunk 1)
chunk 3:  start=800  end=1300  → words[800:1300] (100-word overlap with chunk 2)
                    ↑
              step = 500 - 100 = 400'''
