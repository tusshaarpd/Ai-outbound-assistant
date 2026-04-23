"""Deterministic pre-flight. Runs every guardrail BEFORE the crew kickoff,
so opted-out contacts, rate-limited contacts, and paused agencies never
consume an LLM call. Lives here (not in crew/) so it is callable without
crewai installed — important for CI and the offline eval."""
from memory.brand_voice import get_agency
from memory.contact_history import get_contact

from . import kill_switch, opt_out, rate_limiter
from .human_review_gate import is_required as human_review_required


def preflight_guardrails(contact_id: str, agency_id: str, channel: str) -> dict:
    """Return {'ok': bool, 'stage': str, 'reason': str, 'human_review_required': bool?}."""
    contact = get_contact(contact_id)
    if not contact:
        return {"ok": False, "stage": "lookup", "reason": f"contact_not_found:{contact_id}"}
    agency = get_agency(agency_id)
    if not agency:
        return {"ok": False, "stage": "lookup", "reason": f"agency_not_found:{agency_id}"}

    if kill_switch.is_paused(agency_id):
        return {
            "ok": False,
            "stage": "kill_switch",
            "reason": agency.get("pause_reason") or "agency_paused",
        }

    if opt_out.is_opted_out(contact_id):
        return {"ok": False, "stage": "opt_out", "reason": "contact_opted_out"}

    ok, reason = rate_limiter.can_send(agency_id, contact_id)
    if not ok:
        return {"ok": False, "stage": "rate_limiter", "reason": reason}

    if contact["region"] == "EU" and not contact["has_gdpr_basis"]:
        return {"ok": False, "stage": "compliance", "reason": "missing_gdpr_legal_basis"}
    if channel in ("sms", "voice") and not contact["has_tcpa_consent"]:
        return {"ok": False, "stage": "compliance", "reason": "missing_tcpa_consent"}

    return {
        "ok": True,
        "stage": "ready",
        "reason": "ok",
        "human_review_required": human_review_required(agency_id),
    }
