"""Opt-out list + footer injection."""
from guardrails.opt_out import inject, is_opted_out
from memory.brand_voice import get_agency


def test_opted_out_seed_contacts_are_detected():
    assert is_opted_out("c_009") is True
    assert is_opted_out("c_010") is True
    assert is_opted_out("c_001") is False


def test_inject_email_footer_appends_unsubscribe():
    agency = get_agency("acme_gyms")
    out = inject("Hi Maya, quick question.", "email", agency)
    assert "Reply STOP to unsubscribe" in out
    assert agency["physical_address"] in out


def test_inject_is_idempotent():
    agency = get_agency("acme_gyms")
    once = inject("Hi. Reply STOP to unsubscribe.", "email", agency)
    twice = inject(once, "email", agency)
    # Second call must NOT add a second footer
    assert once == twice


def test_inject_sms_footer():
    agency = get_agency("acme_gyms")
    out = inject("Hey - check this out", "sms", agency)
    assert "Reply STOP" in out
