"""Compliance: CAN-SPAM, GDPR, TCPA — binary rules."""
from guardrails.compliance import check_compliance
from memory.brand_voice import get_agency
from memory.contact_history import get_contact


def _msg(body: str) -> dict:
    return {"subject": "Hello", "body": body}


def test_us_email_without_unsubscribe_blocks():
    contact = get_contact("c_001")
    agency = get_agency("acme_gyms")
    ok, reason = check_compliance(
        contact, _msg("Hi, quick note about your gym."), "email", agency
    )
    assert not ok
    assert reason == "missing_can_spam_opt_out"


def test_us_email_with_unsubscribe_and_address_passes():
    contact = get_contact("c_001")
    agency = get_agency("acme_gyms")
    ok, reason = check_compliance(
        contact,
        _msg("Hi, quick note. Reply STOP to unsubscribe."),
        "email",
        agency,
    )
    assert ok, reason
    assert reason == "ok"


def test_eu_without_gdpr_basis_blocks():
    contact = get_contact("c_006")  # Berlin Fit, has_gdpr_basis=False
    agency = get_agency("acme_gyms")
    ok, reason = check_compliance(
        contact,
        _msg("Hi. Reply STOP to unsubscribe."),
        "email",
        agency,
    )
    assert not ok
    assert reason == "missing_gdpr_legal_basis"


def test_eu_with_gdpr_basis_passes():
    contact = get_contact("c_025")  # has_gdpr_basis=True
    agency = get_agency("acme_gyms")
    ok, reason = check_compliance(
        contact,
        _msg("Hi. Reply STOP to unsubscribe."),
        "email",
        agency,
    )
    assert ok, reason


def test_sms_without_tcpa_consent_blocks():
    contact = get_contact("c_004")  # US, has_tcpa_consent=False
    agency = get_agency("acme_gyms")
    ok, reason = check_compliance(
        contact, _msg("Hi. Reply STOP to stop."), "sms", agency
    )
    assert not ok
    assert reason == "missing_tcpa_consent"


def test_sms_with_tcpa_consent_passes():
    contact = get_contact("c_001")  # has_tcpa_consent=True
    agency = get_agency("acme_gyms")
    ok, reason = check_compliance(
        contact, _msg("Hi. Reply STOP to stop."), "sms", agency
    )
    assert ok, reason


def test_missing_physical_address_blocks_us_email():
    contact = get_contact("c_001")
    agency = get_agency("spammy_test_co")  # physical_address=None
    ok, reason = check_compliance(
        contact, _msg("Hi. Reply STOP to unsubscribe."), "email", agency
    )
    assert not ok
    assert reason == "missing_can_spam_physical_address"
