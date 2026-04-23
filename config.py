"""Central config: env vars, model IDs, guardrail thresholds, paths."""
import os
from pathlib import Path

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

# --- Model routing (see spec Part 2) ---
RESEARCHER_MODEL = os.getenv("RESEARCHER_MODEL", "gpt-4o-mini")
DRAFTER_MODEL = os.getenv("DRAFTER_MODEL", "claude-sonnet-4-5-20250929")
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", "claude-opus-4-7")
MANAGER_MODEL = os.getenv("MANAGER_MODEL", "claude-opus-4-7")

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
