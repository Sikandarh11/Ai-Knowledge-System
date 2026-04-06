"""
google_auth_manager.py
----------------------
Centralized Google OAuth2 authentication manager.
Handles token storage, refresh, and re-authentication for all Google services.

Usage:
    from backend.services.google_auth_manager import get_credentials, get_service

    creds = get_credentials()
    gmail = get_service("gmail", "v1")
    calendar = get_service("calendar", "v3")
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("google_auth_manager")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Unified scopes for all Google services used in this project.
SCOPES: list[str] = [
    "openid",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Resolve paths relative to this file so the module works regardless of
# the working directory from which the application is launched.
_BASE_DIR: Path = Path(__file__).resolve().parent.parent  # backend/
_SECRETS_DIR: Path = _BASE_DIR / "secrets"
CREDENTIALS_PATH: Path = _SECRETS_DIR / "credentials.json"
TOKEN_PATH: Path = _SECRETS_DIR / "token.json"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_token() -> Optional[Credentials]:
    """
    Attempt to load existing credentials from the JSON token file.

    Returns:
        Credentials if the file exists and is valid JSON, otherwise None.
    """
    if not TOKEN_PATH.exists():
        logger.info("No token file found at '%s'.", TOKEN_PATH)
        return None

    try:
        logger.info("Loading token from '%s'.", TOKEN_PATH)
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        return creds
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        # Token file exists but is corrupt or malformed — treat as absent.
        logger.warning("Token file is invalid and will be ignored: %s", exc)
        return None


def _save_token(creds: Credentials) -> None:
    """
    Persist credentials to the JSON token file.

    Args:
        creds: Valid Credentials object to serialise.
    """
    # Ensure the secrets directory exists before writing.
    _SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        token_data = creds.to_json()
        TOKEN_PATH.write_text(token_data, encoding="utf-8")
        logger.info("Token saved to '%s'.", TOKEN_PATH)
    except OSError as exc:
        logger.error("Failed to save token to '%s': %s", TOKEN_PATH, exc)


def _refresh_credentials(creds: Credentials) -> bool:
    """
    Attempt to refresh expired credentials in-place.

    Args:
        creds: Expired Credentials object that still has a refresh token.

    Returns:
        True if the refresh succeeded, False otherwise.
    """
    logger.info("Access token expired — attempting automatic refresh.")
    try:
        creds.refresh(Request())
        logger.info("Token refreshed successfully.")
        return True
    except RefreshError as exc:
        logger.warning("Token refresh failed (RefreshError): %s", exc)
    except TransportError as exc:
        logger.warning("Token refresh failed (TransportError): %s", exc)
    except Exception as exc:  # noqa: BLE001 — catch-all for unexpected errors
        logger.warning("Token refresh failed (unexpected error): %s", exc)
    return False


def _run_oauth_flow() -> Credentials:
    """
    Launch the interactive OAuth2 consent flow via a local server.

    Raises:
        FileNotFoundError: If credentials.json is missing.
        RuntimeError: If the flow completes without returning valid credentials.

    Returns:
        Fresh Credentials obtained from the consent screen.
    """
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found at '{CREDENTIALS_PATH}'. "
            "Download it from the Google Cloud Console and place it in "
            "backend/secrets/credentials.json."
        )

    logger.info("Starting OAuth2 flow — a browser window will open for consent.")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=SCOPES,
        # Ensure a refresh token is always included in the response.
        # access_type and prompt are passed as kwargs to run_local_server
        # which forwards them to the authorization URL construction.
    )

    creds: Credentials = flow.run_local_server(
        port=0,           # let the OS pick a free port
        access_type="offline",   # request a refresh token
        prompt="consent",        # force the consent screen (guarantees refresh_token)
    )

    if not creds:
        raise RuntimeError("OAuth flow completed but returned no credentials.")

    logger.info("OAuth2 flow completed successfully.")
    return creds

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_credentials() -> Credentials:
    """
    Return valid, non-expired Google OAuth2 credentials.

    Resolution order:
      1. Load existing token from disk.
      2. If expired but a refresh token is present → refresh automatically.
      3. If refresh fails, or no token exists → run the interactive OAuth flow.
      4. Persist updated / new credentials back to disk.

    Returns:
        A valid, non-expired :class:`google.oauth2.credentials.Credentials`
        instance ready for use with any Google API client.

    Raises:
        FileNotFoundError: If credentials.json is missing when a new flow
            needs to be started.
    """
    creds: Optional[Credentials] = _load_token()

    # --- Case 1: Token exists and is still valid ---------------------------
    if creds and creds.valid:
        logger.info("Using existing valid credentials.")
        return creds

    # --- Case 2: Token exists but has expired; try to refresh --------------
    if creds and creds.expired and creds.refresh_token:
        if _refresh_credentials(creds):
            _save_token(creds)
            return creds
        # Refresh failed — fall through to a fresh OAuth flow below.
        logger.warning(
            "Refresh token is no longer valid. "
            "Re-authenticating via the OAuth consent screen."
        )

    # --- Case 3: No usable token — run the interactive OAuth flow ----------
    creds = _run_oauth_flow()
    _save_token(creds)
    return creds


def get_service(service_name: str, version: str) -> Resource:
    """
    Build and return an authenticated Google API service client.

    Args:
        service_name: The Google API name, e.g. ``"gmail"`` or ``"calendar"``.
        version:      The API version string, e.g. ``"v1"`` or ``"v3"``.

    Returns:
        A :class:`googleapiclient.discovery.Resource` object ready for use.

    Example::

        gmail    = get_service("gmail", "v1")
        calendar = get_service("calendar", "v3")
        people   = get_service("people", "v1")
    """
    creds: Credentials = get_credentials()
    service: Resource = build(service_name, version, credentials=creds)
    logger.info("Built '%s' (%s) service client.", service_name, version)
    return service