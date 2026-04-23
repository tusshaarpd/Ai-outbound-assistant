"""SQLite bootstrap: schema + seed loader. Idempotent — safe to call repeatedly."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import DB_PATH, SEED_AGENCIES, SEED_CONTACTS

SCHEMA = """
CREATE TABLE IF NOT EXISTS contact_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contact_id TEXT NOT NULL,
  agency_id TEXT NOT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  event_type TEXT NOT NULL,
  payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_contact_ts ON contact_history(contact_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_agency_ts ON contact_history(agency_id, timestamp);

CREATE TABLE IF NOT EXISTS agency_state (
  agency_id TEXT PRIMARY KEY,
  name TEXT,
  status TEXT DEFAULT 'active',
  messages_sent_total INTEGER DEFAULT 0,
  pause_reason TEXT,
  paused_at DATETIME,
  physical_address TEXT,
  brand_voice_json TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
  contact_id TEXT PRIMARY KEY,
  name TEXT,
  email TEXT,
  company TEXT,
  title TEXT,
  region TEXT,
  domain TEXT,
  has_gdpr_basis INTEGER DEFAULT 0,
  has_tcpa_consent INTEGER DEFAULT 0,
  opted_out INTEGER DEFAULT 0,
  last_contacted DATETIME,
  linkedin_summary TEXT,
  quality_note TEXT
);

CREATE TABLE IF NOT EXISTS guardrail_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  agency_id TEXT,
  contact_id TEXT,
  guardrail TEXT NOT NULL,
  action TEXT NOT NULL,
  reason TEXT
);
"""


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create schema and load seed data if tables are empty."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM agency_state")
        if cur.fetchone()[0] == 0:
            _load_agencies(conn)
        cur.execute("SELECT COUNT(*) FROM contacts")
        if cur.fetchone()[0] == 0:
            _load_contacts(conn)
            _seed_recent_events(conn)


def _load_agencies(conn: sqlite3.Connection) -> None:
    agencies = json.loads(Path(SEED_AGENCIES).read_text())
    for a in agencies:
        conn.execute(
            """INSERT INTO agency_state
               (agency_id, name, status, messages_sent_total, pause_reason,
                physical_address, brand_voice_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                a["agency_id"],
                a["name"],
                a.get("status", "active"),
                a.get("messages_sent_total", 0),
                a.get("pause_reason"),
                a.get("physical_address"),
                json.dumps(a.get("brand_voice", {})),
            ),
        )


def _load_contacts(conn: sqlite3.Connection) -> None:
    contacts = json.loads(Path(SEED_CONTACTS).read_text())
    for c in contacts:
        email = c.get("email", "")
        domain = email.split("@", 1)[1] if "@" in email else ""
        conn.execute(
            """INSERT INTO contacts
               (contact_id, name, email, company, title, region, domain,
                has_gdpr_basis, has_tcpa_consent, opted_out, last_contacted,
                linkedin_summary, quality_note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                c["contact_id"],
                c["name"],
                email,
                c.get("company"),
                c.get("title"),
                c.get("region"),
                domain,
                int(bool(c.get("has_gdpr_basis"))),
                int(bool(c.get("has_tcpa_consent"))),
                int(bool(c.get("opted_out"))),
                c.get("last_contacted"),
                c.get("linkedin_summary"),
                c.get("quality_note"),
            ),
        )


def _seed_recent_events(conn: sqlite3.Connection) -> None:
    """For contacts whose seed marks last_contacted='RECENT', log a real event
    in the history table 2h ago so the rate limiter finds it."""
    from datetime import datetime, timedelta
    rows = conn.execute(
        "SELECT contact_id FROM contacts WHERE last_contacted = 'RECENT'"
    ).fetchall()
    two_h_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat(sep=" ")
    for r in rows:
        conn.execute(
            """INSERT INTO contact_history
               (contact_id, agency_id, timestamp, event_type, payload)
               VALUES (?, ?, ?, 'sent', '{}')""",
            (r["contact_id"], "acme_gyms", two_h_ago),
        )
        conn.execute(
            "UPDATE contacts SET last_contacted = ? WHERE contact_id = ?",
            (two_h_ago, r["contact_id"]),
        )


def reset_db() -> None:
    """Destructive: drop + reseed. Used by tests."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()
