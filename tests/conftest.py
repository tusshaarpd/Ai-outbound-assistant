"""Pytest fixtures: fresh SQLite DB per test file."""
import sys
from pathlib import Path

import pytest

# Make repo root importable when running `pytest` from anywhere.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Point every test at an isolated SQLite file and reseed it."""
    import config
    db = tmp_path / "test_outbound.db"
    monkeypatch.setattr(config, "DB_PATH", db)
    # memory.db caches the path at import time via `from config import DB_PATH`,
    # so also patch the already-imported module attribute.
    import memory.db as mdb
    monkeypatch.setattr(mdb, "DB_PATH", db)
    mdb.init_db()
    yield
