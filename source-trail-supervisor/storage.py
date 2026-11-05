"""Profile-scoped SQLite storage for source-trail-supervisor."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

PLUGIN_NAME = "source-trail-supervisor"
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
            CREATE TABLE IF NOT EXISTS source_packets (
                packet_id TEXT PRIMARY KEY,
                ts REAL NOT NULL,
                packet_sha256 TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                anchors_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                packet_id TEXT NOT NULL,
                status TEXT NOT NULL,
                report_sha256 TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS supervisor_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                session_id TEXT NOT NULL,
                node_title TEXT NOT NULL,
                hypothesis TEXT NOT NULL DEFAULT '',
                evidence_ref TEXT NOT NULL DEFAULT '',
                alternative_branch TEXT NOT NULL DEFAULT '',
                outcome TEXT NOT NULL DEFAULT 'open',
                fingerprint TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                session_id TEXT NOT NULL,
                step_kind TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT ''
            )
            """
        )
