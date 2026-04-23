"""Read past outreach events for a contact."""
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from memory.contact_history import list_recent_events


class ContactHistoryInput(BaseModel):
    contact_id: str = Field(..., description="Contact ID to look up")


class ContactHistoryTool(BaseTool):
    name: str = "Contact Outreach History"
    description: str = (
        "Return the last 30 days of outreach events for a contact: what was sent, "
        "when, whether it was opened, replied to, or unsubscribed. Use this to avoid "
        "repeating outreach."
    )
    args_schema: Type[BaseModel] = ContactHistoryInput

    def _run(self, contact_id: str) -> dict:
        events = [e for e in list_recent_events(limit=200) if e["contact_id"] == contact_id]
        return {
            "contact_id": contact_id,
            "event_count": len(events),
            "events": [
                {
                    "timestamp": e["timestamp"],
                    "event_type": e["event_type"],
                    "agency_id": e["agency_id"],
                }
                for e in events[:20]
            ],
        }
