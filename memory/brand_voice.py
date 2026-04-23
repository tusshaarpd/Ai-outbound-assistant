"""Per-agency brand voice + state helpers."""
import json
from datetime import datetime
from typing import Optional

from memory.db import connect, init_db


def get_agency(agency_id: str) -> Optional[dict]:
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM agency_state WHERE agency_id = ?", (agency_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["brand_voice"] = json.loads(d["brand_voice_json"] or "{}")
        return d


def list_agencies() -> list[dict]:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM agency_state ORDER BY agency_id").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["brand_voice"] = json.loads(d["brand_voice_json"] or "{}")
            out.append(d)
        return out


def get_brand_voice(agency_id: str) -> dict:
    a = get_agency(agency_id)
    return a["brand_voice"] if a else {}


def increment_sent(agency_id: str, n: int = 1) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE agency_state SET messages_sent_total = messages_sent_total + ? WHERE agency_id = ?",
            (n, agency_id),
        )


def pause_agency(agency_id: str, reason: str) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE agency_state
               SET status = 'paused', pause_reason = ?, paused_at = ?
               WHERE agency_id = ?""",
            (reason, datetime.utcnow().isoformat(sep=" "), agency_id),
        )


def resume_agency(agency_id: str) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE agency_state
               SET status = 'active', pause_reason = NULL, paused_at = NULL
               WHERE agency_id = ?""",
            (agency_id,),
        )
