"""CAN-SPAM, GDPR, TCPA compliance rules. Deterministic — no LLM judgment."""
from memory.db import connect


def check_compliance(
    contact: dict, message: dict, channel: str, agency: dict
) -> tuple[bool, str]:
    """Return (ok, reason). Blocks are BINARY — never probabilistic."""
    region = contact.get("region")
    body = (message.get("body") or "").lower()

    # CAN-SPAM (US email)
    if region == "US" and channel == "email":
        has_opt_out_language = any(
            phrase in body for phrase in ["unsubscribe", "reply stop", "opt out", "opt-out"]
        )
        if not has_opt_out_language:
            return False, "missing_can_spam_opt_out"
        if not agency.get("physical_address"):
            return False, "missing_can_spam_physical_address"

    # GDPR (EU — any channel, any contact)
    if region == "EU" and not contact.get("has_gdpr_basis"):
        return False, "missing_gdpr_legal_basis"

    # TCPA (SMS/voice)
    if channel in ("sms", "voice") and not contact.get("has_tcpa_consent"):
        return False, "missing_tcpa_consent"

    return True, "ok"


def log_block(agency_id: str, contact_id: str, reason: str) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO guardrail_log (agency_id, contact_id, guardrail, action, reason)
               VALUES (?, ?, 'compliance', 'block', ?)""",
            (agency_id, contact_id, reason),
        )
