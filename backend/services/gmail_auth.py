"""
gmail_auth.py

Gmail OAuth 2.0 authentication module.

Flow:
    1. Look for an existing token.json.
    2. If found, load credentials and auto-refresh if expired.
    3. If not found (or irrecoverably invalid), launch browser OAuth flow
       and persist the resulting token to token.json for future runs.
    4. Return a ready-to-use Gmail API service object.

Dependencies:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
"""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Add extra scopes here if you need more than read-only access, e.g.:
#   "https://www.googleapis.com/auth/gmail.send"
SCOPES: list[str] = [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send"
                    ]

# Default file locations — override via authenticate_gmail() parameters.
DEFAULT_CREDENTIALS_FILE = PROJECT_ROOT / "backend" / "secrets" / "credentials.json"
DEFAULT_TOKEN_FILE        = PROJECT_ROOT / "backend" / "secrets" / "token.pickle"

API_NAME    = "gmail"
API_VERSION = "v1"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_path(path_value: str | Path, *, must_exist: bool) -> Path:
    """
    Resolve a user-provided path in a cwd-safe way.

    For relative inputs, we try the current working directory first,
    then project-root-relative, then backend-relative. This allows calls like
    ``backend/secrets/credentials.json`` to work regardless of whether the
    process starts in repository root or in ``backend``.
    """
    input_path = Path(path_value)
    if input_path.is_absolute():
        return input_path

    candidates: list[Path] = [
        Path.cwd() / input_path,
        PROJECT_ROOT / input_path,
    ]

    if not input_path.parts or input_path.parts[0].lower() != "backend":
        candidates.append(PROJECT_ROOT / "backend" / input_path)

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        resolved_candidate = candidate.resolve(strict=False)
        if resolved_candidate not in seen:
            seen.add(resolved_candidate)
            unique_candidates.append(resolved_candidate)

    for candidate in unique_candidates:
        if candidate.exists():
            return candidate

    if not must_exist:
        for candidate in unique_candidates:
            if candidate.parent.exists():
                return candidate

    return unique_candidates[0]

def _load_credentials(token_path: Path) -> Credentials | None:
    """
    Load existing OAuth credentials from *token_path*.

    Returns ``None`` (rather than raising) when the file is absent or
    structurally invalid so the caller can fall back to the browser flow.

    Args:
        token_path: Path to the persisted token JSON file.

    Returns:
        A :class:`google.oauth2.credentials.Credentials` object, or ``None``.
    """
    if not token_path.exists():
        logger.debug("Token file not found: %s", token_path)
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        logger.debug("Loaded credentials from %s", token_path)
        return creds
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load token file (%s): %s — will re-authenticate.", token_path, exc)
        return None


def _refresh_credentials(creds: Credentials) -> bool:
    """
    Attempt an in-place token refresh.

    Args:
        creds: Expired (but refreshable) credentials.

    Returns:
        ``True`` on success, ``False`` if the refresh token is missing or
        the refresh request failed.
    """
    if not creds.refresh_token:
        logger.warning("No refresh token present — cannot refresh silently.")
        return False

    try:
        creds.refresh(Request())
        logger.info("Access token refreshed successfully.")
        return True
    except RefreshError as exc:
        logger.warning("Token refresh failed (RefreshError): %s", exc)
        return False
    except TransportError as exc:
        logger.warning("Token refresh failed (network error): %s", exc)
        return False


def _has_required_scopes(creds: Credentials, required_scopes: list[str]) -> bool:
    """Return True when credentials include all scopes required by this app."""
    try:
        return creds.has_scopes(required_scopes)
    except Exception:  # noqa: BLE001
        # Be conservative: if we cannot verify scopes, force re-consent.
        return False


def _run_browser_flow(credentials_path: Path) -> Credentials:
    """
    Launch the OAuth 2.0 browser consent flow and return new credentials.

    Opens the system browser once; the user grants access and the resulting
    token is returned for the caller to persist.

    Args:
        credentials_path: Path to the ``credentials.json`` file downloaded
                          from Google Cloud Console.

    Returns:
        Fresh :class:`google.oauth2.credentials.Credentials`.

    Raises:
        FileNotFoundError: If *credentials_path* does not exist.
        Exception: Propagates any error from the OAuth flow itself.
    """
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found: {credentials_path}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )

    logger.info("Launching browser OAuth flow using %s …", credentials_path)
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)

    # run_local_server opens the browser and spins up a temporary HTTP server
    # on localhost to capture the redirect with the auth code.
    creds = flow.run_local_server(port=0, prompt="consent")
    logger.info("Browser OAuth flow completed successfully.")
    return creds


def _save_credentials(creds: Credentials, token_path: Path) -> None:
    """
    Persist *creds* to *token_path* as JSON.

    Creates parent directories if they do not exist.  Logs a warning instead
    of raising if the write fails so the caller can still return the service.

    Args:
        creds:      Credentials to serialise.
        token_path: Destination path for ``token.json``.
    """
    try:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        logger.info("Credentials saved to %s", token_path)
    except OSError as exc:
        logger.warning("Could not save credentials to %s: %s", token_path, exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def authenticate_gmail(
    credentials_path: str | Path = DEFAULT_CREDENTIALS_FILE,
    token_path:        str | Path = DEFAULT_TOKEN_FILE,
) -> object:
    """
    Authenticate with the Gmail API and return a ready-to-use service object.

    Authentication strategy (in order):
        1. Load existing token from *token_path*.
        2. If the token is expired but has a refresh token, refresh it silently.
        3. If no valid token exists, open the browser OAuth consent screen once
           and persist the resulting token to *token_path*.

    The browser is only opened when *token_path* does not exist or is
    irrecoverably invalid.  All subsequent runs reuse the stored token.

    Args:
        credentials_path: Path to the ``credentials.json`` file from Google
                          Cloud Console.  Defaults to ``./credentials.json``.
        token_path:       Path where the OAuth token is stored / loaded.
                          Defaults to ``./token.json``.

    Returns:
        A ``googleapiclient.discovery.Resource`` object for the Gmail v1 API.
        Use it directly::

            service = authenticate_gmail()
            profile = service.users().getProfile(userId="me").execute()

    Raises:
        FileNotFoundError: If *credentials_path* is missing and no valid token
                           exists (i.e. a browser flow is required).
        googleapiclient.errors.HttpError: If the API service cannot be built.

    Example::

        from gmail_auth import authenticate_gmail

        service = authenticate_gmail(
            credentials_path="secrets/credentials.json",
            token_path="secrets/token.json",
        )
        results = service.users().messages().list(userId="me", maxResults=5).execute()
        for msg in results.get("messages", []):
            print(msg["id"])
    """
    credentials_path = _resolve_path(credentials_path, must_exist=True)
    print(f"Authenticating Gmail API with credentials from {credentials_path}")
    token_path       = _resolve_path(token_path, must_exist=False)

    creds: Credentials | None = _load_credentials(token_path)

    if creds and not _has_required_scopes(creds, SCOPES):
        logger.info(
            "Stored token is missing required scopes; starting browser OAuth flow."
        )
        creds = _run_browser_flow(credentials_path)
        _save_credentials(creds, token_path)

    if creds and creds.valid:
        logger.info("Using existing valid credentials from %s", token_path)

    elif creds and creds.expired:
        logger.info("Credentials expired — attempting silent refresh …")
        refreshed = _refresh_credentials(creds)
        if refreshed:
            _save_credentials(creds, token_path)
        else:
            logger.info("Silent refresh failed — falling back to browser flow.")
            creds = _run_browser_flow(credentials_path)
            _save_credentials(creds, token_path)

    else:
        # No token file, or file was unreadable
        logger.info("No valid credentials found — starting browser OAuth flow.")
        creds = _run_browser_flow(credentials_path)
        _save_credentials(creds, token_path)

    try:
        service = build(API_NAME, API_VERSION, credentials=creds)
        logger.info("Gmail API service built successfully (v%s).", API_VERSION)
        return service
    except HttpError as exc:
        logger.exception("Failed to build Gmail service: %s", exc)
        raise