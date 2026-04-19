import os
import tempfile
from fastapi import UploadFile, HTTPException
from backend.ingestion.loaders import detect_file_type

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_DOCUMENT_SIZE_BYTES = 500 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024


async def handle_upload(file: UploadFile) -> dict:
    """
    Validate and save an uploaded file to a temporary directory.

    Args:
        file: FastAPI UploadFile object from a multipart/form-data request.

    Returns:
        {
            "file_path": str,   # absolute path to the saved temp file
            "file_type": str,   # e.g. ".pdf"
            "filename":  str,   # original filename as uploaded
        }

    Raises:
        HTTPException 400: if the file extension is not supported.
    """
    # ── 1. Validate extension ──────────────────────────────────────────────────
    filename = file.filename or ""
    try:
        ext = detect_file_type(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ── 2. Save to a named temp file (preserving extension) ───────────────────
    tmp_dir  = tempfile.mkdtemp(prefix="workspace_upload_")
    tmp_path = os.path.join(tmp_dir, filename)

    written = 0
    try:
        with open(tmp_path, "wb") as buffer:
            while True:
                chunk = file.file.read(READ_CHUNK_SIZE)
                if not chunk:
                    break

                written += len(chunk)
                if written > MAX_DOCUMENT_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="File too large. Maximum allowed size is 500MB.",
                    )

                buffer.write(chunk)
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.isdir(tmp_dir):
            os.rmdir(tmp_dir)

        if isinstance(exc, HTTPException):
            raise

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(exc)}",
        ) 
    finally:
        file.file.close()

    # ── 3. Return metadata ─────────────────────────────────────────────────────
    return {
        "file_path": tmp_path,
        "file_type": ext,
        "filename":  filename,
    }