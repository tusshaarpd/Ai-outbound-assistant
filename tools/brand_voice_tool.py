"""Load an agency's brand voice profile."""
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from memory.brand_voice import get_agency


class BrandVoiceInput(BaseModel):
    agency_id: str = Field(..., description="Agency ID to load brand voice for")


class BrandVoiceTool(BaseTool):
    name: str = "Brand Voice Profile Loader"
    description: str = (
        "Load the agency's brand voice profile: tone, formality, forbidden words, "
        "preferred closings, and brand story. Match this voice exactly when drafting "
        "or reviewing copy."
    )
    args_schema: Type[BaseModel] = BrandVoiceInput

    def _run(self, agency_id: str) -> dict:
        agency = get_agency(agency_id)
        if not agency:
            return {"error": f"Agency {agency_id} not found"}
        return {
            "agency_id": agency_id,
            "agency_name": agency["name"],
            "physical_address": agency["physical_address"],
            "brand_voice": agency["brand_voice"],
        }
