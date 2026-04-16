"""
test_email.py

CLI test script for the full email pipeline:
    Gmail auth → fetch emails → process with LLM

Flow:
    1. authenticate_gmail()      — loads token.json (no browser if it exists)
    2. fetch_emails()            — pulls latest inbox emails via Gmail API
    3. process_email()           — summarise / classify / reply via OpenAI
    4. Print structured output   — subject, summary, intent, reply

Usage:
    python backend/tests/test_email.py
    python backend/tests/test_email.py --max 3 --tone concise
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from pprint import pformat
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# Path setup — allow running directly: python backend/tests/test_email.py
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_openai_key_from_dotenv(project_root: Path) -> None:
    """
    Load OPENAI_API_KEY from project-root .env file if not already set.

    This keeps the test runnable via direct script execution without requiring
    callers to export the variable manually in every shell session.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return

    env_path = project_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key == "OPENAI_API_KEY" and value:
            os.environ["OPENAI_API_KEY"] = value
            return


_load_openai_key_from_dotenv(PROJECT_ROOT)

from backend.services.google_auth_manager import get_credentials
from backend.tools.email_tool import fetch_emails
from backend.services.email_service import process_email, process_emails_bulk

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,          # suppress debug noise during tests
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

DIVIDER       = "=" * 64
SECTION_LINE  = "-" * 64


def _print_header(title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


def _print_email_result(index: int, result: dict) -> None:
    """Pretty-print a single processed email result."""
    print(f"\n{'=' * 64}")
    print(f"  EMAIL {index + 1}")
    print(f"{'-' * 64}")
    print(f"  Subject : {result.get('subject', '—')}")
    print(f"  From    : {result.get('sender',  '—')}")
    print(f"{'-' * 64}")

    print("\n  SUMMARY")
    print(f"  {SECTION_LINE[2:]}")
    summary = result.get("summary") or "(none)"
    for line in summary.strip().splitlines():
        print(f"  {line}")

    print("\n  INTENT")
    print(f"  {SECTION_LINE[2:]}")
    intent = result.get("intent") or "(none)"
    for line in intent.strip().splitlines():
        print(f"  {line}")

    print(f"\n  REPLY  [tone: {result.get('reply_tone', 'formal')}]")
    print(f"  {SECTION_LINE[2:]}")
    reply = result.get("reply") or "(none)"
    for line in reply.strip().splitlines():
        print(f"  {line}")

    print(f"\n{'=' * 64}")


def _print_fetch_summary(emails: list[dict]) -> None:
    """Print a compact table of fetched emails before processing."""
    _print_header(f"FETCHED {len(emails)} EMAIL(S)")
    for i, email in enumerate(emails, 1):
        subject = email.get("subject", "(No subject)")[:55]
        sender  = email.get("sender",  "(Unknown)")[:40]
        print(f"  [{i:>2}]  {subject:<57}  {sender}")
    print()


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_fetch_and_process(
    service,
    max_results: int = 5,
    tone: str = "formal",
) -> None:
    """
    CASE 1 — Full pipeline: fetch + process each email individually.

    Fetches up to *max_results* emails from the inbox, then runs the
    full summarise / classify / reply pipeline on each one.
    """
    _print_header("CASE 1 — Full pipeline (individual process_email)")

    # --- Fetch --------------------------------------------------------------
    print("  Fetching emails from Gmail …")
    fetch_result = fetch_emails(service, max_results=max_results)

    if not fetch_result["success"]:
        print(f"\n  [FAIL] fetch_emails error: {fetch_result['error']}")
        return

    emails = fetch_result["data"]
    if not emails:
        print("\n  [SKIP] No emails found in inbox.")
        return

    _print_fetch_summary(emails)

    # --- Process one by one -------------------------------------------------
    for idx, email in enumerate(emails):
        print(f"\n  Processing email {idx + 1}/{len(emails)} …")
        result = process_email(email, reply_tone=tone)

        if not result["success"]:
            print(f"\n  [FAIL] process_email error: {result['error']}")
            continue

        _print_email_result(idx, result["data"])


def test_bulk_processing(
    service,
    max_results: int = 3,
    tone: str = "concise",
) -> None:
    """
    CASE 2 — Bulk pipeline: fetch all then call process_emails_bulk.

    Demonstrates batch processing with a shared EmailAgent instance
    and concise replies.
    """
    _print_header("CASE 2 — Bulk pipeline (process_emails_bulk)")

    print("  Fetching emails from Gmail …")
    fetch_result = fetch_emails(service, max_results=max_results)

    if not fetch_result["success"]:
        print(f"\n  [FAIL] fetch_emails error: {fetch_result['error']}")
        return

    emails = fetch_result["data"]
    if not emails:
        print("\n  [SKIP] No emails found in inbox.")
        return

    _print_fetch_summary(emails)

    print(f"  Running bulk processing on {len(emails)} email(s) …\n")
    bulk_result = process_emails_bulk(emails, reply_tone=tone, skip_on_error=True)

    if not bulk_result["success"]:
        print(f"\n  [FAIL] process_emails_bulk error: {bulk_result['error']}")
        return

    data = bulk_result["data"]
    print(f"  Total: {data['total']}  |  Succeeded: {data['succeeded']}  |  Failed: {data['failed']}")

    for idx, item in enumerate(data["processed"]):
        _print_email_result(idx, item)

    if data["errors"]:
        print("\n  ERRORS")
        print(f"  {SECTION_LINE}")
        for err in data["errors"]:
            print(f"  [email {err['index']}] {err['subject'][:50]} — {err['error']}")


def test_bad_input() -> None:
    """
    CASE 3 — Validation: pass a malformed email dict.

    Confirms the service returns a structured error rather than raising.
    """
    _print_header("CASE 3 — Bad input (missing body)")

    bad_email = {
        "id":      "fake_id",
        "subject": "Test email with no body",
        "sender":  "nobody@example.com",
        # body and body_clean intentionally omitted
    }

    result = process_email(bad_email)

    print(f"  success : {result['success']}")
    print(f"  error   : {result['error']}")

    expected = not result["success"] and result["error"]
    status = "[PASS]" if expected else "[FAIL]"
    print(f"\n  {status} Validation behaved as expected: {bool(expected)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CLI test for the Gmail fetch + LLM processing pipeline.",
    )
    parser.add_argument(
        "--max", type=int, default=5,
        help="Maximum number of emails to fetch (default: 5).",
    )
    parser.add_argument(
        "--tone", choices=["formal", "friendly", "concise"], default="formal",
        help="Reply tone for generated responses (default: formal).",
    )
    parser.add_argument(
        "--case", choices=["1", "2", "3", "all"], default="all",
        help="Which test case to run: 1=individual, 2=bulk, 3=bad-input, all (default: all).",
    )
    parser.add_argument(
        "--credentials",
        default=str(PROJECT_ROOT / "backend" / "services" / "credentials.json"),
        help="Path to Google OAuth credentials.json (default: backend/services/credentials.json).",
    )
    parser.add_argument(
        "--token",
        default=str(PROJECT_ROOT / "backend" / "services" / "token.json"),
        help="Path to stored OAuth token.json (default: backend/services/token.json).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("\n[FAIL] OPENAI_API_KEY is not set.")
        print("Set it in your shell, or add OPENAI_API_KEY=... to a project-root .env file.")
        print("Example (Git Bash): export OPENAI_API_KEY='sk-...'")
        print("Example (PowerShell): $env:OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    # --- Authenticate (uses token.json — no browser if it already exists) ---
    _print_header("GMAIL AUTHENTICATION")
    print(f"  credentials : {args.credentials}")
    print(f"  token       : {args.token}")
    print(f"  (browser login only triggered when {args.token} is absent)\n")

    try:
        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)
        print("  [OK] Authenticated successfully.")
    except FileNotFoundError as exc:
        print(f"\n  [FAIL] {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n  [FAIL] Authentication error: {exc}")
        sys.exit(1)

    # --- Run selected test cases --------------------------------------------
    run_all  = args.case == "all"

    if run_all or args.case == "1":
        test_fetch_and_process(service, max_results=args.max, tone=args.tone)

    if run_all or args.case == "2":
        test_bulk_processing(service, max_results=min(args.max, 3), tone="concise")

    if run_all or args.case == "3":
        test_bad_input()

    _print_header("ALL TESTS COMPLETE")


# if __name__ == "__main__":
#     main()

from backend.services.google_auth_manager import get_credentials
from googleapiclient.discovery import build
from backend.tools.email_tool import fetch_emails
from backend.services.email_service import process_email

creds = get_credentials()
service = build("gmail", "v1", credentials=creds)
emails = fetch_emails(service, max_results=1)["data"]
print(process_email(emails[0])["data"]["reply"])