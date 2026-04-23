"""Mock LinkedIn profile fetcher. Returns the seed `linkedin_summary` plus
inferred signals. In production: swap for real enrichment API."""
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from memory.contact_history import get_contact


class LinkedInInput(BaseModel):
    contact_id: str = Field(..., description="Contact ID to look up")


class LinkedInProfileTool(BaseTool):
    name: str = "LinkedIn Profile Lookup"
    description: str = (
        "Fetch public LinkedIn signals for a contact: recent posts, job changes, "
        "activity level, and likely seniority. Returns 'unknown' when data is missing "
        "rather than fabricating."
    )
    args_schema: Type[BaseModel] = LinkedInInput

    def _run(self, contact_id: str) -> dict:
        contact = get_contact(contact_id)
        if not contact:
            return {"error": f"Contact {contact_id} not found"}
        summary = contact.get("linkedin_summary") or ""
        if not summary:
            return {
                "contact_id": contact_id,
                "summary": "unknown",
                "recent_signals": [],
                "is_decision_maker": "unknown",
            }
        title = (contact.get("title") or "").lower()
        is_dm = any(
            k in title
            for k in ["owner", "founder", "ceo", "partner", "principal", "director", "manager"]
        )
        is_student = "student" in title or "intern" in title
        return {
            "contact_id": contact_id,
            "summary": summary,
            "recent_signals": [s.strip() for s in summary.split(".") if s.strip()],
            "is_decision_maker": False if is_student else is_dm,
            "is_student_or_job_seeker": is_student,
        }
