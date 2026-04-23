"""Rate limiter: deterministic thresholds. No LLM involved."""
from datetime import datetime, timedelta

from guardrails.rate_limiter import can_send
from memory.contact_history import log_event


def test_happy_path_allows_send():
    ok, reason = can_send("acme_gyms", "c_001")
    assert ok, reason
    assert reason == "ok"


def test_recent_seed_blocks_c_011():
    """c_011 is marked last_contacted='RECENT' in seed → a sent event was
    logged 2h ago → per_contact_daily_cap must trigger."""
    ok, reason = can_send("acme_gyms", "c_011")
    assert not ok
    assert reason == "per_contact_daily_cap"


def test_duplicate_send_within_24h_blocks():
    log_event("c_002", "acme_gyms", "sent")
    ok, reason = can_send("acme_gyms", "c_002")
    assert not ok
    assert reason == "per_contact_daily_cap"


def test_sequence_cap_blocks_after_five_sends():
    now = datetime.utcnow()
    for i in range(5):
        log_event(
            "c_003",
            "acme_gyms",
            "sent",
            timestamp=now - timedelta(days=(i + 1) * 2),
        )
    ok, reason = can_send("acme_gyms", "c_003")
    assert not ok
    assert reason == "per_contact_sequence_cap"


def test_domain_hourly_cap_blocks():
    """Seed 50 sends in the last hour from the same domain → per-domain cap."""
    # All seed contacts in the same domain pattern aren't here, so use
    # same-domain direct injection via the contacts table isn't needed:
    # just log 50 events for contacts that share c_001's domain.
    # Simpler: log directly to contact_history for 50 distinct fake contacts
    # on the same domain. We use c_001's real domain by inserting events.
    import sqlite3
    from memory.db import connect

    with connect() as conn:
        # Insert 50 contacts on the same domain + 50 sent events in the past hour
        for i in range(50):
            cid = f"dom_{i}"
            conn.execute(
                """INSERT INTO contacts
                   (contact_id, name, email, company, domain)
                   VALUES (?, ?, ?, ?, ?)""",
                (cid, f"Dom {i}", f"dom{i}@ironworksgym.com", "Ironworks", "ironworksgym.com"),
            )
            conn.execute(
                """INSERT INTO contact_history
                   (contact_id, agency_id, timestamp, event_type, payload)
                   VALUES (?, 'acme_gyms', ?, 'sent', '{}')""",
                (cid, datetime.utcnow().isoformat(sep=" ")),
            )
    # c_001 is also on ironworksgym.com → next send hits the cap
    ok, reason = can_send("acme_gyms", "c_001")
    assert not ok
    assert reason == "per_domain_hourly_cap"
