"""Mock calendar tool: returns three available slots."""
from datetime import datetime, timedelta
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class CalendarInput(BaseModel):
    agency_id: str = Field(..., description="Agency ID requesting slots")
    timezone: str = Field("America/New_York", description="IANA timezone string")


class CalendarTool(BaseTool):
    name: str = "Calendar Slot Finder"
    description: str = (
        "Return three available 30-minute meeting slots over the next 5 business days. "
        "Used when the outreach message needs a concrete booking link."
    )
    args_schema: Type[BaseModel] = CalendarInput

    def _run(self, agency_id: str, timezone: str = "America/New_York") -> dict:
        base = datetime.utcnow().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        slots = [
            (base + timedelta(days=i, hours=hr)).isoformat()
            for i, hr in [(0, 14), (1, 10), (2, 15)]
        ]
        return {
            "agency_id": agency_id,
            "timezone": timezone,
            "slots_iso": slots,
        }
