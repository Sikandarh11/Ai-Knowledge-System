from fastapi import APIRouter, UploadFile, File
from backend.ingestion.uploader import handle_upload

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("")
async def upload_file(file: UploadFile = File(...)):
    result = await handle_upload(file)
    return result
'''

**Example Postman request:**
```
Method:   POST
URL:      http://127.0.0.1:8000/upload
Body:     form-data
  key:    file   (type = File)
  value:  select your .pdf / .docx / .txt
  '''