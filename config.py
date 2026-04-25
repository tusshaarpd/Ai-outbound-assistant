"""Central config: env vars, model IDs, guardrail thresholds, paths.

API keys are sourced in this order:
1. Streamlit Cloud `st.secrets` (promoted into os.environ by secrets_loader)
2. Local `.env` file (loaded by python-dotenv)
3. Process env vars

If only ONE provider key is present, model routing collapses to that provider
so the demo still runs with a single API key.
"""
import os
from pathlib import Path

import secrets_loader  # noqa: F401 — side-effect: promote st.secrets into env
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "outbound.db"
SEED_CONTACTS = DATA_DIR / "seed_contacts.json"
SEED_AGENCIES = DATA_DIR / "seed_agencies.json"
GOLDEN_DATASET = ROOT / "evals" / "golden_dataset.json"

# --- API keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

HAS_OPENAI = bool(OPENAI_API_KEY) and not OPENAI_API_KEY.startswith("sk-...")
HAS_ANTHROPIC = bool(ANTHROPIC_API_KEY) and not ANTHROPIC_API_KEY.startswith("sk-ant-...")

# --- Model routing ---
# Default routing (spec Part 2) requires both providers. If only one key is
# present, every agent routes to the available provider. Users can still pin
# specific model IDs via env / secrets — those wins.

_DEFAULT_OPENAI_CHEAP = "gpt-4o-mini"
_DEFAULT_OPENAI_SMART = "gpt-4o"
_DEFAULT_ANTHROPIC_SONNET = "claude-sonnet-4-5-20250929"
_DEFAULT_ANTHROPIC_OPUS = "claude-opus-4-7"


def _route(role_default: str, openai_only: str, anthropic_only: str) -> str:
    """Pick a model ID based on which providers are configured."""
    if HAS_OPENAI and HAS_ANTHROPIC:
        return role_default
    if HAS_OPENAI:
        return openai_only
    if HAS_ANTHROPIC:
        return anthropic_only
    return role_default  # No keys: keep the default; app will surface a banner.


RESEARCHER_MODEL = os.getenv(
    "RESEARCHER_MODEL",
    _route(_DEFAULT_OPENAI_CHEAP, _DEFAULT_OPENAI_CHEAP, _DEFAULT_ANTHROPIC_SONNET),
)
DRAFTER_MODEL = os.getenv(
    "DRAFTER_MODEL",
    _route(_DEFAULT_ANTHROPIC_SONNET, _DEFAULT_OPENAI_SMART, _DEFAULT_ANTHROPIC_SONNET),
)
REVIEWER_MODEL = os.getenv(
    "REVIEWER_MODEL",
    _route(_DEFAULT_ANTHROPIC_OPUS, _DEFAULT_OPENAI_SMART, _DEFAULT_ANTHROPIC_OPUS),
)
MANAGER_MODEL = os.getenv(
    "MANAGER_MODEL",
    _route(_DEFAULT_ANTHROPIC_OPUS, _DEFAULT_OPENAI_SMART, _DEFAULT_ANTHROPIC_OPUS),
)

# --- Rate limits (spec Part 6.1) ---
RATE_LIMITS = {
    "per_contact_per_day": 1,
    "per_contact_per_sequence": 5,
    "per_agency_per_day_default": 100,
    "per_agency_per_day_established": 2000,
    "per_domain_per_hour": 50,
}
ESTABLISHED_AGENCY_MIN_MESSAGES = 1000

# --- Kill switch thresholds (spec Part 6.3) ---
KILL_THRESHOLDS = {
    "spam_complaint_rate_24h": float(os.getenv("SPAM_COMPLAINT_KILL_THRESHOLD", "0.001")),
    "unsubscribe_rate_7d": float(os.getenv("UNSUBSCRIBE_KILL_THRESHOLD", "0.02")),
    "bounce_rate_24h": float(os.getenv("BOUNCE_KILL_THRESHOLD", "0.05")),
}

# --- Human review gate ---
HUMAN_REVIEW_THRESHOLD_MESSAGES = int(os.getenv("HUMAN_REVIEW_THRESHOLD_MESSAGES", "1000"))

# --- Demo / ops ---
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
CREWAI_VERBOSE = os.getenv("CREWAI_VERBOSE", "true").lower() == "true"


def configured_providers() -> list[str]:
    out: list[str] = []
    if HAS_OPENAI:
        out.append("openai")
    if HAS_ANTHROPIC:
        out.append("anthropic")
    return out
