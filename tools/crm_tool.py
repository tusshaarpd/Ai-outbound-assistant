"""CRM reader tool. Deterministic wrapper over SQLite contacts table."""
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from memory.contact_history import get_contact


class CRMReadInput(BaseModel):
    contact_id: str = Field(..., description="The contact's unique ID (e.g. 'c_001')")


class CRMReadTool(BaseTool):
    name: str = "CRM Contact Reader"
    description: str = (
        "Read full contact details from the CRM given a contact_id. "
        "Returns name, email, company, title, region, consent flags, and opt-out status."
    )
    args_schema: Type[BaseModel] = CRMReadInput

    def _run(self, contact_id: str) -> dict:
        contact = get_contact(contact_id)
        if not contact:
            return {"error": f"Contact {contact_id} not found"}
        return {
            "contact_id": contact["contact_id"],
            "name": contact["name"],
            "email": contact["email"],
            "company": contact["company"],
            "title": contact["title"],
            "region": contact["region"],
            "has_gdpr_basis": contact["has_gdpr_basis"],
            "has_tcpa_consent": contact["has_tcpa_consent"],
            "opted_out": contact["opted_out"],
            "last_contacted": contact["last_contacted"],
        }
