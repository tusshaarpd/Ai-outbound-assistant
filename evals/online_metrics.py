"""Online KPI aggregator. Reads contact_history and computes the 5 metrics
from spec 8.2, with rep override rate highlighted as the north-star."""
from dataclasses import dataclass
from typing import Optional

from memory.contact_history import count_events


@dataclass
class OnlineMetrics:
    sent_30d: int
    response_rate: float
    meeting_booked_rate: float
    unsubscribe_rate: float
    spam_complaint_rate: float
    rep_override_rate: float  # north-star


def _safe_rate(num: int, den: int) -> float:
    return (num / den) if den > 0 else 0.0


def compute(agency_id: Optional[str] = None, window_hours: int = 720) -> OnlineMetrics:
    scope = {"agency_id": agency_id, "within_hours": window_hours}
    sent = count_events(event_type="sent", **scope)
    replied = count_events(event_type="replied", **scope)
    booked = count_events(event_type="meeting_booked", **scope)
    unsubs = count_events(event_type="unsubscribed", **scope)
    complaints = count_events(event_type="complained", **scope)
    drafted = count_events(event_type="drafted", **scope)
    edited = count_events(event_type="rep_edited", **scope)
    return OnlineMetrics(
        sent_30d=sent,
        response_rate=_safe_rate(replied, sent),
        meeting_booked_rate=_safe_rate(booked, sent),
        unsubscribe_rate=_safe_rate(unsubs, sent),
        spam_complaint_rate=_safe_rate(complaints, sent),
        rep_override_rate=_safe_rate(edited, drafted),
    )


TARGETS = {
    "response_rate": ("≥", 0.08),
    "meeting_booked_rate": ("≥", 0.015),
    "unsubscribe_rate": ("<", 0.01),
    "spam_complaint_rate": ("<", 0.0008),
    "rep_override_rate": ("<", 0.15),
}


def target_status(metric: str, value: float) -> str:
    op, threshold = TARGETS[metric]
    hit = (value >= threshold) if op == "≥" else (value < threshold)
    return "on_target" if hit else "off_target"
