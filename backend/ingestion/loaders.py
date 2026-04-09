from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def detect_file_type(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext or '(none)'}'. Allowed types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return ext
