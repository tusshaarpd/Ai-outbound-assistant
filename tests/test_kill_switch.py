"""Kill switch: auto-pause agency when rates exceed thresholds."""
from guardrails.kill_switch import evaluate_agency_health, is_paused
from memory.brand_voice import get_agency, resume_agency
from memory.contact_history import log_event


def test_healthy_agency_not_paused():
    resume_agency("acme_gyms")
    # Log a few clean sends
    for _ in range(20):
        log_event("c_001", "acme_gyms", "sent")
    result = evaluate_agency_health("acme_gyms")
    assert result["status"] == "healthy"
    assert is_paused("acme_gyms") is False


def test_spam_complaint_rate_triggers_pause():
    resume_agency("acme_gyms")
    for _ in range(1000):
        log_event("c_001", "acme_gyms", "sent")
    # 2 complaints on 1000 sends = 0.002 > 0.001 threshold
    for _ in range(2):
        log_event("c_001", "acme_gyms", "complained")
    result = evaluate_agency_health("acme_gyms")
    assert result["status"] == "paused"
    assert "spam_complaint_threshold" in result["triggers"]
    assert is_paused("acme_gyms") is True


def test_unsubscribe_rate_triggers_pause():
    resume_agency("lawyer_growth_co")
    for _ in range(100):
        log_event("c_004", "lawyer_growth_co", "sent")
    # 3 unsubscribes on 100 sends = 0.03 > 0.02 threshold
    for _ in range(3):
        log_event("c_004", "lawyer_growth_co", "unsubscribed")
    result = evaluate_agency_health("lawyer_growth_co")
    assert result["status"] == "paused"
    assert "unsubscribe_threshold" in result["triggers"]


def test_bounce_rate_triggers_pause():
    resume_agency("acme_gyms")
    for _ in range(100):
        log_event("c_001", "acme_gyms", "sent")
    # 6 bounces on 100 sends = 0.06 > 0.05 threshold
    for _ in range(6):
        log_event("c_001", "acme_gyms", "bounced")
    result = evaluate_agency_health("acme_gyms")
    assert result["status"] == "paused"
    assert "bounce_threshold" in result["triggers"]


def test_spammy_test_co_ships_as_paused():
    """Seed guarantee: demo-ready paused agency."""
    a = get_agency("spammy_test_co")
    assert a is not None
    assert a["status"] == "paused"
