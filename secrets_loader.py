"""Promote Streamlit Cloud secrets into os.environ before any other module
reads them. Safe to import outside Streamlit (in tests, CLI, etc.) — it
silently no-ops if `st.secrets` is unavailable or empty.

Import this BEFORE `config` or anything that touches API keys.

OpenAI-only deploy: only OPENAI_API_KEY is promoted as a provider key.
"""
import os

PROMOTED_KEYS = (
    "OPENAI_API_KEY",
    # Optional model overrides — let users tune routing from secrets.toml too.
    "RESEARCHER_MODEL",
    "DRAFTER_MODEL",
    "REVIEWER_MODEL",
    "MANAGER_MODEL",
    "SENDER_MODEL",
    # Optional guardrail tunables
    "SPAM_COMPLAINT_KILL_THRESHOLD",
    "UNSUBSCRIBE_KILL_THRESHOLD",
    "BOUNCE_KILL_THRESHOLD",
    "HUMAN_REVIEW_THRESHOLD_MESSAGES",
    "DEMO_MODE",
    "CREWAI_VERBOSE",
)


def load_streamlit_secrets() -> dict:
    """Try to read st.secrets and copy whitelisted keys into os.environ.
    Returns the dict of keys that were actually promoted (for logging)."""
    try:
        import streamlit as st  # noqa: WPS433
    except ImportError:
        return {}

    try:
        secrets = st.secrets
    except (FileNotFoundError, AttributeError):
        return {}
    except Exception:  # noqa: BLE001 — Streamlit raises a custom error type
        return {}

    promoted = {}
    for key in PROMOTED_KEYS:
        try:
            value = secrets.get(key)
        except (KeyError, AttributeError):
            continue
        if value and not os.environ.get(key):
            os.environ[key] = str(value)
            promoted[key] = "***" if "KEY" in key else str(value)
    return promoted


# Run on import.
PROMOTED = load_streamlit_secrets()


def _alias_chroma_key() -> None:
    """CrewAI's built-in memory uses ChromaDB, which needs its own env var
    for OpenAI embeddings. Alias from OPENAI_API_KEY so users don't have
    to set the same key twice."""
    if os.environ.get("OPENAI_API_KEY") and not os.environ.get("CHROMA_OPENAI_API_KEY"):
        os.environ["CHROMA_OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]


def _strip_anthropic_overrides() -> None:
    """Defensive: if a stale ANTHROPIC_API_KEY or claude-* model override is
    in the env (left over from older .env / secrets.toml templates), wipe
    it. This deploy is OpenAI-only and we never want litellm to attempt an
    Anthropic call."""
    os.environ.pop("ANTHROPIC_API_KEY", None)
    for var in ("RESEARCHER_MODEL", "DRAFTER_MODEL", "REVIEWER_MODEL",
                "MANAGER_MODEL", "SENDER_MODEL"):
        val = os.environ.get(var, "")
        if val.startswith(("claude-", "anthropic/")):
            os.environ.pop(var, None)


_alias_chroma_key()
_strip_anthropic_overrides()
