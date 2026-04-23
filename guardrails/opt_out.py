"""Opt-out list + opt-out language injector."""
from memory.contact_history import get_contact


CAN_SPAM_FOOTER_EMAIL = (
    "\n\n—\nYou're receiving this because we thought it might be relevant. "
    "Reply STOP to unsubscribe. {address}"
)

CAN_SPAM_FOOTER_SMS = "\nReply STOP to unsubscribe."


def is_opted_out(contact_id: str) -> bool:
    c = get_contact(contact_id)
    return bool(c and c.get("opted_out"))


def inject(body: str, channel: str, agency: dict) -> str:
    """Append the correct opt-out language for the channel. Idempotent."""
    if "reply stop" in body.lower() or "unsubscribe" in body.lower():
        return body
    if channel == "email":
        address = agency.get("physical_address") or ""
        return body + CAN_SPAM_FOOTER_EMAIL.format(address=address)
    if channel == "sms":
        return body + CAN_SPAM_FOOTER_SMS
    return body
