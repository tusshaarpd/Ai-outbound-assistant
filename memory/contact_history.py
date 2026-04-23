"""Read/write helpers for contacts + event log."""
import json
from datetime import datetime, timedelta
from typing import Any, Optional

from memory.db import connect, init_db


def _row_to_contact(row) -> dict:
    d = dict(row)
    d["has_gdpr_basis"] = bool(d["has_gdpr_basis"])
    d["has_tcpa_consent"] = bool(d["has_tcpa_consent"])
    d["opted_out"] = bool(d["opted_out"])
    return d


def get_contact(contact_id: str) -> Optional[dict]:
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM contacts WHERE contact_id = ?", (contact_id,)
        ).fetchone()
        return _row_to_contact(row) if row else None


def list_contacts() -> list[dict]:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM contacts ORDER BY contact_id").fetchall()
        return [_row_to_contact(r) for r in rows]


def log_event(
    contact_id: str,
    agency_id: str,
    event_type: str,
    payload: Optional[dict] = None,
    timestamp: Optional[datetime] = None,
) -> None:
    with connect() as conn:
        if timestamp is None:
            conn.execute(
                """INSERT INTO contact_history (contact_id, agency_id, event_type, payload)
                   VALUES (?, ?, ?, ?)""",
                (contact_id, agency_id, event_type, json.dumps(payload or {})),
            )
        else:
            conn.execute(
                """INSERT INTO contact_history (contact_id, agency_id, timestamp, event_type, payload)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    contact_id,
                    agency_id,
                    timestamp.isoformat(sep=" "),
                    event_type,
                    json.dumps(payload or {}),
                ),
            )


def count_events(
    *,
    contact_id: Optional[str] = None,
    agency_id: Optional[str] = None,
    domain: Optional[str] = None,
    event_type: Optional[str] = None,
    within_hours: Optional[int] = None,
) -> int:
    clauses: list[str] = []
    params: list[Any] = []
    if contact_id:
        clauses.append("contact_id = ?")
        params.append(contact_id)
    if agency_id:
        clauses.append("agency_id = ?")
        params.append(agency_id)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    if within_hours is not None:
        cutoff = datetime.utcnow() - timedelta(hours=within_hours)
        clauses.append("timestamp >= ?")
        params.append(cutoff.isoformat(sep=" "))

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT COUNT(*) FROM contact_history {where}"

    with connect() as conn:
        if domain:
            # Join against contacts for domain filter
            clauses_d = list(clauses)
            clauses_d.append("c.domain = ?")
            params_d = list(params) + [domain]
            where_d = f"WHERE {' AND '.join(clauses_d)}"
            sql_d = (
                f"SELECT COUNT(*) FROM contact_history h "
                f"JOIN contacts c ON c.contact_id = h.contact_id {where_d}"
            )
            return conn.execute(sql_d, params_d).fetchone()[0]
        return conn.execute(sql, params).fetchone()[0]


def list_recent_events(
    agency_id: Optional[str] = None, limit: int = 100
) -> list[dict]:
    init_db()
    with connect() as conn:
        if agency_id:
            rows = conn.execute(
                """SELECT * FROM contact_history WHERE agency_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (agency_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contact_history ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["payload"] = json.loads(d["payload"]) if d["payload"] else {}
            except json.JSONDecodeError:
                d["payload"] = {}
            out.append(d)
        return out


def get_contact_domain(contact_id: str) -> str:
    c = get_contact(contact_id)
    return c["domain"] if c else ""


def set_opted_out(contact_id: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE contacts SET opted_out = 1 WHERE contact_id = ?", (contact_id,)
        )
