"""Mock email sender. In DEMO_MODE, logs to DB and returns a fake message_id.
In production, swaps to a real ESP client."""
import uuid
from datetime import datetime
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import DEMO_MODE
from memory.brand_voice import increment_sent
from memory.contact_history import log_event


class EmailSendInput(BaseModel):
    contact_id: str = Field(..., description="Contact ID the message is sent to")
    agency_id: str = Field(..., description="Sending agency ID")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body (opt-out language already injected)")
    to_email: Optional[str] = Field(None, description="Optional override of recipient email")


class EmailSendTool(BaseTool):
    name: str = "Email Send"
    description: str = (
        "Send an email to a contact. In demo mode this logs the send to the event DB "
        "and returns a synthetic message_id. Returns status and timestamp."
    )
    args_schema: Type[BaseModel] = EmailSendInput

    def _run(
        self,
        contact_id: str,
        agency_id: str,
        subject: str,
        body: str,
        to_email: Optional[str] = None,
    ) -> dict:
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.utcnow().isoformat()
        if DEMO_MODE:
            log_event(
                contact_id,
                agency_id,
                "sent",
                {
                    "channel": "email",
                    "subject": subject,
                    "body": body,
                    "message_id": message_id,
                    "to_email": to_email,
                },
            )
            increment_sent(agency_id)
            return {
                "status": "sent",
                "message_id": message_id,
                "timestamp": timestamp,
                "mode": "demo",
            }
        return {
            "status": "error",
            "reason": "real SMTP not implemented — set DEMO_MODE=true",
            "timestamp": timestamp,
        }
