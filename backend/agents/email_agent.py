"""
email_agent.py

LLM-based email processing agent.

Responsibilities:
    - Summarise incoming emails
    - Detect urgency / intent
    - Generate contextual replies

No Gmail API logic lives here — pass in parsed email dicts produced by
``backend.tools.email_tool.fetch_emails()``.

Follows the same architectural pattern as scheduling_agent.py:
    - A class (EmailAgent) owns the LLM client and exposes public methods
    - Prompts are isolated in dedicated _build_*_prompt() helpers
    - Every public method returns a plain string (or raises on hard failure)
    - A module-level convenience wrapper mirrors run_agent() in scheduling_agent
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL       = "gpt-4o-mini"
DEFAULT_MAX_TOKENS  = 512
DEFAULT_TEMPERATURE = 0.3          # low = consistent, deterministic output
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
ToneType = Literal["formal", "friendly", "concise"]


# ---------------------------------------------------------------------------
# Prompt builders  (pure functions — easy to unit-test independently)
# ---------------------------------------------------------------------------

def _build_summarize_prompt(email: dict[str, Any]) -> str:
    """
    Build the summarisation prompt for a single email.

    Args:
        email: Parsed email dict with at least ``subject``, ``sender``, ``body_clean``.

    Returns:
        A fully formatted prompt string ready to send to the LLM.
    """
    return (
        "You are an expert email assistant.\n\n"
        "Summarise the following email in 2-3 concise lines. "
        "Capture the key point, any action required, and the sender's intent. "
        "Do not include greetings or sign-offs.\n\n"
        f"From:    {email.get('sender', 'Unknown')}\n"
        f"Subject: {email.get('subject', '(No subject)')}\n\n"
        f"{email.get('body_clean') or email.get('body', '')}\n\n"
        "Summary:"
    )


def _build_intent_prompt(email: dict[str, Any]) -> str:
    """
    Build the intent-detection prompt for a single email.

    Args:
        email: Parsed email dict.

    Returns:
        A prompt instructing the LLM to classify the email and explain why.
    """
    return (
        "You are an expert email triage assistant.\n\n"
        "Classify the following email as either URGENT or NORMAL.\n\n"
        "An email is URGENT if it:\n"
        "  - Requires a response or action within 24 hours\n"
        "  - Mentions deadlines, outages, or critical issues\n"
        "  - Comes from a senior stakeholder requesting immediate attention\n"
        "  - Contains words like 'ASAP', 'immediately', 'urgent', 'critical'\n\n"
        "Respond with exactly this format (two lines, nothing else):\n"
        "Classification: URGENT or NORMAL\n"
        "Reason: one sentence explaining why\n\n"
        f"From:    {email.get('sender', 'Unknown')}\n"
        f"Subject: {email.get('subject', '(No subject)')}\n\n"
        f"{email.get('body_clean') or email.get('body', '')}"
    )


def _build_reply_prompt(email: dict[str, Any], tone: ToneType) -> str:
    """
    Build the reply-generation prompt for a single email.

    Args:
        email: Parsed email dict.
        tone:  Desired reply tone — ``"formal"``, ``"friendly"``, or ``"concise"``.

    Returns:
        A prompt instructing the LLM to draft a reply in the requested tone.
    """
    tone_instructions: dict[str, str] = {
        "formal": (
            "Write a professional, formal reply. Use polite language, "
            "complete sentences, and a respectful sign-off."
        ),
        "friendly": (
            "Write a warm, friendly reply. Use a conversational tone while "
            "remaining professional. Keep it approachable."
        ),
        "concise": (
            "Write a short, direct reply of 3-5 sentences maximum. "
            "Get to the point immediately with no filler phrases."
        ),
    }
    instruction = tone_instructions.get(tone, tone_instructions["formal"])

    return (
        "You are an expert email assistant helping draft replies.\n\n"
        f"{instruction}\n\n"
        "Address all key points raised in the original email. "
        "Do not invent facts — if information is missing, indicate that you will follow up. "
        "Include an appropriate greeting and sign-off.\n\n"
        "Original email\n"
        "--------------\n"
        f"From:    {email.get('sender', 'Unknown')}\n"
        f"Subject: {email.get('subject', '(No subject)')}\n\n"
        f"{email.get('body_clean') or email.get('body', '')}\n\n"
        "Reply:"
    )


# ---------------------------------------------------------------------------
# LLM client wrapper
# ---------------------------------------------------------------------------

class _OpenAIClient:
    """
    Thin wrapper around the OpenAI Chat Completions API.

    Centralises client construction and the single call pattern so the
    agent methods stay free of boilerplate.

    Args:
        api_key:     OpenAI API key. Defaults to ``OPENAI_API_KEY`` env var.
        model:       Model name (default ``gpt-4o-mini``).
        max_tokens:  Maximum tokens in the completion (default 512).
        temperature: Sampling temperature (default 0.3).
    """

    def __init__(
        self,
        api_key:     str | None = None,
        model:       str        = DEFAULT_MODEL,
        max_tokens:  int        = DEFAULT_MAX_TOKENS,
        temperature: float      = DEFAULT_TEMPERATURE,
    ) -> None:
        self.model       = model
        self.max_tokens  = max_tokens
        self.temperature = temperature
        if not api_key:
            api_key = openai_api_key
        self._client     = self._build(api_key)

    def _build(self, api_key: str) -> Any:
        if not api_key:
            raise EnvironmentError(
                "OpenAI API key not found. "
                "Set the OPENAI_API_KEY environment variable or pass api_key= explicitly."
            )
        try:
            import openai  # type: ignore
            return openai.OpenAI(api_key=api_key)
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required. Install it with: pip install openai"
            ) from exc

    def complete(self, system: str, user: str) -> str:
        """
        Send a chat completion request and return the assistant's text.

        Args:
            system: System prompt (role/persona instructions).
            user:   User prompt (the actual task).

        Returns:
            The model's reply as a stripped plain string.

        Raises:
            RuntimeError: Wraps any OpenAI API error with a readable message.
        """
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:  # noqa: BLE001
            logger.exception("OpenAI API call failed: %s", exc)
            raise RuntimeError(f"LLM call failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Email Agent
# ---------------------------------------------------------------------------

class EmailAgent:
    """
    LLM-powered agent for summarising, triaging, and replying to emails.

    All methods accept a parsed email dict (as returned by
    ``backend.tools.email_tool.fetch_emails()``) and return plain strings.

    Args:
        api_key:     OpenAI API key. Defaults to ``OPENAI_API_KEY`` env var.
        model:       OpenAI model to use (default ``gpt-4o-mini``).
        max_tokens:  Maximum tokens per completion (default 512).
        temperature: Sampling temperature (default 0.3).

    Example::

        agent = EmailAgent()

        summary = agent.summarize_email(email)
        intent  = agent.detect_intent(email)
        reply   = agent.generate_reply(email, tone="formal")
    """

    def __init__(
        self,
        api_key:     str | None = None,
        model:       str        = DEFAULT_MODEL,
        max_tokens:  int        = DEFAULT_MAX_TOKENS,
        temperature: float      = DEFAULT_TEMPERATURE,
    ) -> None:
        self._llm = _OpenAIClient(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def summarize_email(self, email: dict[str, Any]) -> str:
        """
        Summarise an email in 2-3 concise lines.

        Captures the key point, any required action, and the sender's intent.
        Does not reproduce greetings or sign-offs.

        Args:
            email: Parsed email dict with ``subject``, ``sender``,
                   ``body_clean`` (or ``body``) keys.

        Returns:
            A 2-3 line plain-text summary string.

        Raises:
            RuntimeError: If the LLM call fails.

        Example::

            summary = agent.summarize_email(email)
            # "Alice is requesting sign-off on the Q2 budget proposal by Friday.
            #  She highlights a 15% cost reduction versus last year.
            #  Action required: review and approve the attached document."
        """
        prompt = _build_summarize_prompt(email)
        logger.info(
            "summarize_email | subject=%r sender=%r",
            email.get("subject"), email.get("sender"),
        )
        result = self._llm.complete(
            system="You are a concise email summarisation assistant.",
            user=prompt,
        )
        logger.debug("summarize_email result: %s", result)
        return result

    def detect_intent(self, email: dict[str, Any]) -> str:
        """
        Classify an email as URGENT or NORMAL with a brief reason.

        An email is considered URGENT if it requires action within 24 hours,
        mentions critical issues or deadlines, or uses escalatory language.

        Args:
            email: Parsed email dict.

        Returns:
            A two-line string::

                Classification: URGENT
                Reason: The sender requires a decision on the contract by end of day.

        Raises:
            RuntimeError: If the LLM call fails.

        Example::

            intent = agent.detect_intent(email)
            # "Classification: URGENT\\nReason: Deadline is today at 5 PM."
        """
        prompt = _build_intent_prompt(email)
        logger.info(
            "detect_intent | subject=%r sender=%r",
            email.get("subject"), email.get("sender"),
        )
        result = self._llm.complete(
            system="You are an email triage assistant. Reply only in the specified format.",
            user=prompt,
        )
        logger.debug("detect_intent result: %s", result)
        return result

    def generate_reply(
        self,
        email: dict[str, Any],
        tone: ToneType = "formal",
    ) -> str:
        """
        Draft a reply to an email in the requested tone.

        Args:
            email: Parsed email dict.
            tone:  One of:

                   - ``"formal"``   — professional, polite, complete sentences.
                   - ``"friendly"`` — warm and approachable but still professional.
                   - ``"concise"``  — 3-5 sentences, direct, no filler.

                   Defaults to ``"formal"``.

        Returns:
            A ready-to-send plain-text reply string (includes greeting and sign-off).

        Raises:
            ValueError:   If *tone* is not one of the accepted values.
            RuntimeError: If the LLM call fails.

        Example::

            reply = agent.generate_reply(email, tone="concise")
            # "Hi Alice,\\n\\nThank you for sending the proposal...\\n\\nBest regards,\\n[Your name]"
        """
        valid_tones: tuple[str, ...] = ("formal", "friendly", "concise")
        if tone not in valid_tones:
            raise ValueError(
                f"Invalid tone {tone!r}. Choose from: {', '.join(valid_tones)}."
            )

        prompt = _build_reply_prompt(email, tone)
        logger.info(
            "generate_reply | tone=%r subject=%r sender=%r",
            tone, email.get("subject"), email.get("sender"),
        )
        result = self._llm.complete(
            system=(
                "You are an expert email assistant that drafts clear, "
                "accurate, and appropriately toned replies."
            ),
            user=prompt,
        )
        logger.debug("generate_reply result: %s", result[:120])
        return result

    def process_email(
        self,
        email: dict[str, Any],
        reply_tone: ToneType = "formal",
    ) -> dict[str, Any]:
        """
        Run all three analyses on a single email in one call.

        Convenience method that calls :meth:`summarize_email`,
        :meth:`detect_intent`, and :meth:`generate_reply` sequentially and
        bundles the results into a single dict.

        Args:
            email:      Parsed email dict.
            reply_tone: Tone for the generated reply (default ``"formal"``).

        Returns:
            ::

                {
                    "id":           "18f3a...",
                    "subject":      "Q2 Budget Proposal",
                    "sender":       "alice@example.com",
                    "summary":      "Alice is requesting sign-off on ...",
                    "intent":       "Classification: URGENT\\nReason: ...",
                    "reply":        "Dear Alice,\\n\\n...",
                    "reply_tone":   "formal",
                    "error":        None
                }

            On partial failure (one step fails) ``error`` contains the message
            and the failed field is set to ``None``.
        """
        result: dict[str, Any] = {
            "id":         email.get("id", ""),
            "subject":    email.get("subject", ""),
            "sender":     email.get("sender", ""),
            "summary":    None,
            "intent":     None,
            "reply":      None,
            "reply_tone": reply_tone,
            "error":      None,
        }

        try:
            result["summary"] = self.summarize_email(email)
            result["intent"]  = self.detect_intent(email)
            result["reply"]   = self.generate_reply(email, tone=reply_tone)
        except Exception as exc:  # noqa: BLE001
            logger.exception("process_email failed: %s", exc)
            result["error"] = str(exc)

        return result

    def send_reply(
        self,
        email: dict[str, Any],
        reply_text: str,
    ) -> dict[str, Any]:
        """
        Build the outgoing email payload for a drafted reply.

        Args:
            email: Parsed incoming email dict.
            reply_text: Reply content to send back to the sender.

        Returns:
            A dict with ``to``, ``subject``, and ``body`` keys.
        """
        return {
            "to": email.get("sender"),
            "subject": f"Re: {email.get('subject')}",
            "body": reply_text,
        }


# ---------------------------------------------------------------------------
# Module-level convenience wrappers
# ---------------------------------------------------------------------------

def summarize_email(
    email: dict[str, Any],
    api_key: str | None = None,
    model:   str        = DEFAULT_MODEL,
) -> str:
    """
    Summarise *email* without instantiating :class:`EmailAgent` manually.

    Args:
        email:   Parsed email dict.
        api_key: OpenAI API key (defaults to ``OPENAI_API_KEY`` env var).
        model:   OpenAI model to use.

    Returns:
        2-3 line summary string.
    """
    return EmailAgent(api_key=api_key, model=model).summarize_email(email)


def detect_intent(
    email: dict[str, Any],
    api_key: str | None = None,
    model:   str        = DEFAULT_MODEL,
) -> str:
    """
    Classify *email* as URGENT or NORMAL without instantiating :class:`EmailAgent` manually.

    Args:
        email:   Parsed email dict.
        api_key: OpenAI API key (defaults to ``OPENAI_API_KEY`` env var).
        model:   OpenAI model to use.

    Returns:
        Two-line classification string.
    """
    return EmailAgent(api_key=api_key, model=model).detect_intent(email)


def generate_reply(
    email: dict[str, Any],
    tone:    ToneType   = "formal",
    api_key: str | None = None,
    model:   str        = DEFAULT_MODEL,
) -> str:
    """
    Draft a reply to *email* without instantiating :class:`EmailAgent` manually.

    Args:
        email:   Parsed email dict.
        tone:    ``"formal"``, ``"friendly"``, or ``"concise"``.
        api_key: OpenAI API key (defaults to ``OPENAI_API_KEY`` env var).
        model:   OpenAI model to use.

    Returns:
        Ready-to-send reply string.
    """
    return EmailAgent(api_key=api_key, model=model).generate_reply(email, tone=tone)


def send_reply(
    email: dict[str, Any],
    reply_text: str,
) -> dict[str, Any]:
    """Build the outgoing email payload for a reply string."""
    return {
        "to": email.get("sender"),
        "subject": f"Re: {email.get('subject')}",
        "body": reply_text,
    }