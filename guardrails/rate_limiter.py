"""Deterministic rate limiter. Per-contact, per-agency, per-domain, per-sequence.
Reads from contact_history event log — never from an LLM."""
from config import ESTABLISHED_AGENCY_MIN_MESSAGES, RATE_LIMITS
from memory.brand_voice import get_agency
from memory.contact_history import count_events, get_contact_domain
from memory.db import connect


def _agency_daily_cap(agency_id: str) -> int:
    a = get_agency(agency_id)
    if a and a.get("messages_sent_total", 0) >= ESTABLISHED_AGENCY_MIN_MESSAGES:
        return RATE_LIMITS["per_agency_per_day_established"]
    return RATE_LIMITS["per_agency_per_day_default"]


def can_send(agency_id: str, contact_id: str) -> tuple[bool, str]:
    """Return (ok, reason). 'ok' is the sentinel for success."""
    # Per-contact per-day (24h rolling)
    if (
        count_events(contact_id=contact_id, event_type="sent", within_hours=24)
        >= RATE_LIMITS["per_contact_per_day"]
    ):
        return False, "per_contact_daily_cap"

    # Per-contact per-sequence (30-day rolling)
    if (
        count_events(contact_id=contact_id, event_type="sent", within_hours=720)
        >= RATE_LIMITS["per_contact_per_sequence"]
    ):
        return False, "per_contact_sequence_cap"

    # Per-agency per-day
    cap = _agency_daily_cap(agency_id)
    if count_events(agency_id=agency_id, event_type="sent", within_hours=24) >= cap:
        return False, "per_agency_daily_cap"

    # Per-domain per-hour
    domain = get_contact_domain(contact_id)
    if domain:
        if (
            count_events(domain=domain, event_type="sent", within_hours=1)
            >= RATE_LIMITS["per_domain_per_hour"]
        ):
            return False, "per_domain_hourly_cap"

    return True, "ok"


def bucket_status(agency_id: str, contact_id: str) -> dict:
    """Used by the Streamlit Guardrails tab — exposes every counter."""
    return {
        "per_contact_24h": count_events(
            contact_id=contact_id, event_type="sent", within_hours=24
        ),
        "per_contact_30d": count_events(
            contact_id=contact_id, event_type="sent", within_hours=720
        ),
        "per_agency_24h": count_events(
            agency_id=agency_id, event_type="sent", within_hours=24
        ),
        "per_agency_cap": _agency_daily_cap(agency_id),
    }


def log_block(agency_id: str, contact_id: str, reason: str) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO guardrail_log (agency_id, contact_id, guardrail, action, reason)
               VALUES (?, ?, 'rate_limiter', 'block', ?)""",
            (agency_id, contact_id, reason),
        )
