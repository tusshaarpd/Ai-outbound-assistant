"""Central config: env vars, model IDs, guardrail thresholds, paths.

OpenAI-only deploy: the only API key required is OPENAI_API_KEY. Anthropic
is intentionally not supported here — every agent routes to an OpenAI model.
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

# --- API key ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
HAS_OPENAI = bool(OPENAI_API_KEY) and not OPENAI_API_KEY.startswith("sk-...")

# --- Model routing (OpenAI-only) ---
# All four agents route to OpenAI. Researcher + Sender use a cheap model
# because they're high-volume and tool-calling. Drafter + Reviewer + Manager
# use a smart model because they need quality judgment / orchestration.
_OPENAI_CHEAP = "gpt-4o-mini"
_OPENAI_SMART = "gpt-4o"


def _model_or(env_var: str, default: str) -> str:
    """Honor an explicit override only if it's an OpenAI model. Silently
    drop any non-OpenAI override (e.g. stale claude-* values from older
    .env / secrets.toml templates) so we never call a provider we can't auth."""
    val = os.getenv(env_var)
    if not val:
        return default
    if val.startswith(("gpt-", "o1-", "o3-", "o4-", "openai/")):
        return val
    return default


RESEARCHER_MODEL = _model_or("RESEARCHER_MODEL", _OPENAI_CHEAP)
DRAFTER_MODEL = _model_or("DRAFTER_MODEL", _OPENAI_SMART)
REVIEWER_MODEL = _model_or("REVIEWER_MODEL", _OPENAI_SMART)
MANAGER_MODEL = _model_or("MANAGER_MODEL", _OPENAI_SMART)
SENDER_MODEL = _model_or("SENDER_MODEL", _OPENAI_CHEAP)

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
    return ["openai"] if HAS_OPENAI else []
