"""Profile-scoped SQLite storage for claim-market-router."""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

PLUGIN_NAME = "claim-market-router"
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
            CREATE TABLE IF NOT EXISTS token_usage_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                session_id TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auction_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                goal_summary TEXT NOT NULL,
                role_needed TEXT NOT NULL,
                complexity INTEGER NOT NULL,
                winner_name TEXT NOT NULL,
                winner_model TEXT NOT NULL,
                resolution_mode TEXT NOT NULL,
                confidence REAL NOT NULL,
                verifier_name TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL
            )
            """
        )


def record_token_usage(
    *,
    session_id: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    conn = get_db()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO token_usage_ledger
                    (ts, session_id, provider, model, prompt_tokens, completion_tokens, total_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    str(session_id or ""),
                    str(provider or ""),
                    str(model or ""),
                    int(prompt_tokens or 0),
                    int(completion_tokens or 0),
                    int(total_tokens or (int(prompt_tokens or 0) + int(completion_tokens or 0))),
                ),
            )
    finally:
        conn.close()


def get_window_usage(window_seconds: float = 86400.0) -> dict[str, Any]:
    cutoff = time.time() - window_seconds
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT model, provider,
                   SUM(prompt_tokens) AS prompt_tokens,
                   SUM(completion_tokens) AS completion_tokens,
                   SUM(total_tokens) AS total_tokens,
                   COUNT(*) AS call_count
            FROM token_usage_ledger
            WHERE ts >= ?
            GROUP BY provider, model
            ORDER BY total_tokens DESC
            """,
            (cutoff,),
        ).fetchall()
        by_model: dict[str, dict[str, Any]] = {}
        total_window_tokens = 0
        for row in rows:
            key = f"{row['provider']}/{row['model']}" if row["provider"] else row["model"]
            tokens = int(row["total_tokens"] or 0)
            total_window_tokens += tokens
            by_model[key] = {
                "provider": row["provider"],
                "model": row["model"],
                "prompt_tokens": int(row["prompt_tokens"] or 0),
                "completion_tokens": int(row["completion_tokens"] or 0),
                "total_tokens": tokens,
                "call_count": int(row["call_count"] or 0),
            }
        return {
            "window_seconds": window_seconds,
            "total_window_tokens": total_window_tokens,
            "by_model": by_model,
        }
    finally:
        conn.close()


def record_auction_receipt(
    *,
    goal_summary: str,
    role_needed: str,
    complexity: int,
    winner_name: str,
    winner_model: str,
    resolution_mode: str,
    confidence: float,
    verifier_name: str,
    payload_json: str,
) -> int:
    conn = get_db()
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO auction_receipts
                    (ts, goal_summary, role_needed, complexity, winner_name,
                     winner_model, resolution_mode, confidence, verifier_name, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    goal_summary[:240],
                    role_needed,
                    int(complexity),
                    winner_name,
                    winner_model,
                    resolution_mode,
                    float(confidence),
                    verifier_name,
                    payload_json,
                ),
            )
            return int(cur.lastrowid or 0)
    finally:
        conn.close()


def list_recent_auctions(limit: int = 10) -> list[dict[str, Any]]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, ts, goal_summary, role_needed, complexity, winner_name,
                   winner_model, resolution_mode, confidence, verifier_name
            FROM auction_receipts
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 100)),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def clear_ledger() -> dict[str, int]:
    conn = get_db()
    try:
        with conn:
            c1 = conn.execute("DELETE FROM token_usage_ledger").rowcount
            c2 = conn.execute("DELETE FROM auction_receipts").rowcount
        return {"deleted_usage_rows": c1, "deleted_auction_rows": c2}
    finally:
        conn.close()
