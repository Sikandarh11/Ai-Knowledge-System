import re


def extract_text(file_path: str, file_type: str) -> str:
    """
    Extract raw text from a PDF, DOCX, or TXT file.

    Args:
        file_path: Absolute path to the saved file.
        file_type: Extension string — ".pdf", ".docx", or ".txt".

    Returns:
        A single clean string of extracted text.

    Raises:
        ValueError: if file_type is not supported.
        RuntimeError: if extraction fails.
    """
    try:
        if file_type == ".pdf":
            raw = _extract_pdf(file_path)
        elif file_type == ".docx":
            raw = _extract_docx(file_path)
        elif file_type == ".txt":
            raw = _extract_txt(file_path)
        else:
            raise ValueError(
                f"Unsupported file type '{file_type}'. "
                "Supported: .pdf, .docx, .txt"
            )
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to extract text from '{file_path}': {str(exc)}")

    return _clean(raw)


# ── Extractors ─────────────────────────────────────────────────────────────────

def _extract_pdf(file_path: str) -> str:
    import fitz  # PyMuPDF

    pages = []
    with fitz.open(file_path) as doc:
        for page in doc:
            pages.append(page.get_text())
    return "\n".join(pages)


def _extract_docx(file_path: str) -> str:
    from docx import Document

    doc        = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _extract_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ── Cleaner ────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    if not text or not text.strip():
        return ""

    # Normalize Windows/Mac line endings → Unix
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse runs of spaces/tabs into a single space
    text = re.sub(r"[ \t]+", " ", text)

    # Strip trailing whitespace from every line
    lines = [line.strip() for line in text.split("\n")]

    # Drop fully empty lines (collapse multiple blank lines into one)
    cleaned_lines = []
    prev_blank    = False
    for line in lines:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue          # skip consecutive blank lines
        cleaned_lines.append(line)
        prev_blank = is_blank

    return "\n".join(cleaned_lines).strip()
'''
---

**Add to `requirements.txt`:**
```
PyMuPDF>=1.24.0
python-docx>=1.1.0
```

---

**How the cleaning pipeline works:**
```
raw text
    │
    ├─ 1. normalize line endings   \r\n / \r  →  \n
    ├─ 2. collapse spaces/tabs     "a   b"    →  "a b"
    ├─ 3. strip each line          " hello "  →  "hello"
    └─ 4. collapse blank lines     3 blanks   →  1 blank
    │
    ▼
one clean string
'''
