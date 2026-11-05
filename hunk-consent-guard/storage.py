"""Profile-scoped SQLite storage for hunk-consent-guard."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

PLUGIN_NAME = "hunk-consent-guard"
TEST_DATA_DIR: Path | None = None


def get_db() -> sqlite3.Connection:
    """Open the profile-scoped plugin SQLite database via Hermes plugin_storage,
    with a safe local fallback when running standalone unit tests outside Hermes.
    """
    if TEST_DATA_DIR is not None:
        db_dir = Path(TEST_DATA_DIR) / PLUGIN_NAME
        db_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_dir / "data.db"), check_same_thread=False)
    else:
        try:
            from plugins.plugin_storage import plugin_db

            conn = plugin_db(PLUGIN_NAME)
        except Exception:
            fallback_root = Path(tempfile.gettempdir()) / "hermes-plugin-data"
            db_dir = fallback_root / PLUGIN_NAME
            db_dir.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_dir / "data.db"), check_same_thread=False)

    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hunk_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                target_path TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                baseline_sha256 TEXT NOT NULL,
                baseline_text TEXT NOT NULL,
                hunks_json TEXT NOT NULL,
                approved_hunks_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rollback_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                source_kind TEXT NOT NULL,
                proposal_id INTEGER,
                target_path TEXT NOT NULL,
                before_sha256 TEXT NOT NULL,
                after_sha256 TEXT NOT NULL,
                before_text TEXT,
                after_text TEXT,
                unified_diff TEXT NOT NULL DEFAULT '',
                rolled_back INTEGER NOT NULL DEFAULT 0
            )
            """
        )
