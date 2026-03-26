import os
import tempfile
import shutil
from fastapi import UploadFile, HTTPException

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


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
    filename  = file.filename or ""
    _, ext    = os.path.splitext(filename.lower())

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext or '(none)'}'. "
                f"Allowed types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    # ── 2. Save to a named temp file (preserving extension) ───────────────────
    tmp_dir  = tempfile.mkdtemp(prefix="workspace_upload_")
    tmp_path = os.path.join(tmp_dir, filename)

    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
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