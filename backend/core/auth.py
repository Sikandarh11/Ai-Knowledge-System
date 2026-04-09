import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: str


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _verify_hs256_signature(token: str, secret: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")

    header_b64, payload_b64, signature_b64 = parts

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload") from exc

    if header.get("alg") != "HS256":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported token algorithm")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_b64 = base64.urlsafe_b64encode(expected_signature).rstrip(b"=").decode("utf-8")

    if not hmac.compare_digest(expected_b64, signature_b64):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    exp = payload.get("exp")
    if exp is not None:
        try:
            if int(exp) < int(time.time()):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token expiration") from exc

    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    secret = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="JWT secret is not configured")

    payload = _verify_hs256_signature(credentials.credentials, secret)

    user_id = payload.get("user_id") or payload.get("sub") or payload.get("uid")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user identifier")

    return CurrentUser(user_id=str(user_id))
