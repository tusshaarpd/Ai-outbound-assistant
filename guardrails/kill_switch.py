"""Auto-pause an agency if complaint/unsubscribe/bounce rates exceed thresholds.
Run on a schedule — in the demo, invoked on every Streamlit refresh."""
from config import KILL_THRESHOLDS
from memory.brand_voice import get_agency, pause_agency
from memory.contact_history import count_events


def _rate(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator > 0 else 0.0


def get_agency_metrics(agency_id: str) -> dict:
    sent_24h = count_events(agency_id=agency_id, event_type="sent", within_hours=24)
    sent_7d = count_events(agency_id=agency_id, event_type="sent", within_hours=168)
    complaints_24h = count_events(
        agency_id=agency_id, event_type="complained", within_hours=24
    )
    unsubs_7d = count_events(
        agency_id=agency_id, event_type="unsubscribed", within_hours=168
    )
    bounces_24h = count_events(
        agency_id=agency_id, event_type="bounced", within_hours=24
    )
    return {
        "sent_24h": sent_24h,
        "sent_7d": sent_7d,
        "spam_complaint_rate_24h": _rate(complaints_24h, sent_24h),
        "unsubscribe_rate_7d": _rate(unsubs_7d, sent_7d),
        "bounce_rate_24h": _rate(bounces_24h, sent_24h),
    }


def evaluate_agency_health(agency_id: str) -> dict:
    metrics = get_agency_metrics(agency_id)
    triggers = []

    if metrics["spam_complaint_rate_24h"] > KILL_THRESHOLDS["spam_complaint_rate_24h"]:
        triggers.append("spam_complaint_threshold")
    if metrics["unsubscribe_rate_7d"] > KILL_THRESHOLDS["unsubscribe_rate_7d"]:
        triggers.append("unsubscribe_threshold")
    if metrics["bounce_rate_24h"] > KILL_THRESHOLDS["bounce_rate_24h"]:
        triggers.append("bounce_threshold")

    if triggers:
        pause_agency(agency_id, ",".join(triggers))
        return {"status": "paused", "triggers": triggers, "metrics": metrics}

    return {"status": "healthy", "metrics": metrics}


def is_paused(agency_id: str) -> bool:
    a = get_agency(agency_id)
    return bool(a and a.get("status") == "paused")
