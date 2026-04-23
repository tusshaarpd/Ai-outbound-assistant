"""Decide when a human must approve a draft before send.
Rule: for a new agency, a human reviews every draft until N successful sends.
After that, drafts flow autonomously."""
from config import HUMAN_REVIEW_THRESHOLD_MESSAGES
from memory.brand_voice import get_agency


def is_required(agency_id: str) -> bool:
    a = get_agency(agency_id)
    if not a:
        return True  # Unknown agency → require human review
    return a.get("messages_sent_total", 0) < HUMAN_REVIEW_THRESHOLD_MESSAGES
