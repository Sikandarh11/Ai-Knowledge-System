from typing import Any, Dict

from pydantic import BaseModel


class VoiceResponse(BaseModel):
    type: str
    status: str
    message: str
    data: Dict[str, Any] = {}
