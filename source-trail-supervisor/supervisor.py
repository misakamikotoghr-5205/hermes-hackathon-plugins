"""Session progress fingerprinter, stuck-loop detector, and causal decision-node logger.

Adapted from:
- misakamikotoghr-5205/codex-session-supervisor (fingerprint_progress, stuck detection, node logging)
- misakamikotoghr-5205/deadlock-manor (causal decision branches & postmortem replay)
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .storage import get_db

_ACTIVE_STUCK_THRESHOLD: int = 4


def set_active_stuck_threshold(threshold: int) -> None:
    global _ACTIVE_STUCK_THRESHOLD
    _ACTIVE_STUCK_THRESHOLD = max(2, int(threshold))


def get_active_stuck_threshold() -> int:
    return _ACTIVE_STUCK_THRESHOLD


def compute_step_fingerprint(tool_name: str, args: Any, error_flag: bool) -> str:
    """Create a deterministic short hash of (tool_name, canonicalized args keys/targets, error_flag)."""
    if isinstance(args, dict):
        # Focus on target keys rather than timestamps
        filtered = {
            k: str(v)[:120]
            for k, v in sorted(args.items())
            if k in ("path", "file_path", "target_path", "command", "query", "url", "expression", "packet_id")
        }
        payload = f"{tool_name}|err={int(error_flag)}|{json.dumps(filtered, sort_keys=True)}"
    else:
        payload = f"{tool_name}|err={int(error_flag)}|{str(args)[:120]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def record_step_and_check_stuck(
    *,
    session_id: str,
    step_kind: str,
    fingerprint: str,
    detail: str = "",
    stuck_threshold: int = 4,
) -> dict[str, Any]:
    """Record a step fingerprint and detect whether the session is stuck in a loop."""
    sid = str(session_id or "default")
    conn = get_db()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO session_fingerprints (ts, session_id, step_kind, fingerprint, detail)
                VALUES (?, ?, ?, ?, ?)
                """,
                (time.time(), sid, step_kind, fingerprint, detail[:240]),
            )

        recent = conn.execute(
            """
            SELECT fingerprint, step_kind, detail, ts
            FROM session_fingerprints
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (sid, max(4, int(stuck_threshold) * 2)),
        ).fetchall()

        fps = [r["fingerprint"] for r in recent]
        threshold = max(2, int(stuck_threshold))
        set_active_stuck_threshold(threshold)
        is_stuck = False
        loop_pattern = ""

        # Pattern 1: N identical consecutive fingerprints
        if len(fps) >= threshold and len(set(fps[:threshold])) == 1:
            is_stuck = True
            loop_pattern = f"identical_repeat({threshold}x:{fps[0]})"
        # Pattern 2: ABAB oscillation across 2*threshold or >=4 steps
        elif len(fps) >= 4 and fps[0] == fps[2] and fps[1] == fps[3] and fps[0] != fps[1]:
            is_stuck = True
            loop_pattern = f"abab_oscillation({fps[0]}<->{fps[1]})"

        return {
            "session_id": sid,
            "is_stuck": is_stuck,
            "loop_pattern": loop_pattern,
            "recent_count": len(fps),
            "latest_fingerprint": fingerprint,
        }
    finally:
        conn.close()


def record_decision_node(
    *,
    session_id: str,
    node_title: str,
    hypothesis: str = "",
    evidence_ref: str = "",
    alternative_branch: str = "",
    outcome: str = "open",
    fingerprint: str = "",
) -> dict[str, Any]:
    """Log a recoverable causal decision node in SQLite."""
    sid = str(session_id or "default")
    conn = get_db()
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO supervisor_nodes
                    (ts, session_id, node_title, hypothesis, evidence_ref,
                     alternative_branch, outcome, fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    sid,
                    node_title.strip(),
                    hypothesis.strip(),
                    evidence_ref.strip(),
                    alternative_branch.strip(),
                    outcome.strip() or "open",
                    fingerprint.strip(),
                ),
            )
            node_id = int(cur.lastrowid or 0)
        return {
            "ok": True,
            "node_id": node_id,
            "session_id": sid,
            "node_title": node_title,
            "outcome": outcome,
        }
    finally:
        conn.close()


def get_supervisor_overview(session_id: str = "default", stuck_threshold: int | None = None) -> dict[str, Any]:
    """Return the session's decision-node DAG, progress fingerprint history, and recovery remedies."""
    sid = str(session_id or "default")
    effective_threshold = max(2, int(stuck_threshold if stuck_threshold is not None else get_active_stuck_threshold()))
    conn = get_db()
    try:
        nodes = conn.execute(
            """
            SELECT id, ts, session_id, node_title, hypothesis, evidence_ref,
                   alternative_branch, outcome, fingerprint
            FROM supervisor_nodes
            WHERE session_id = ? OR ? = 'all'
            ORDER BY id DESC
            LIMIT 25
            """,
            (sid, sid),
        ).fetchall()

        steps = conn.execute(
            """
            SELECT id, ts, step_kind, fingerprint, detail
            FROM session_fingerprints
            WHERE session_id = ? OR ? = 'all'
            ORDER BY id DESC
            LIMIT 12
            """,
            (sid, sid),
        ).fetchall()

        fps = [r["fingerprint"] for r in steps]
        threshold = effective_threshold
        is_stuck = False
        remedy = "Session is progressing normally; distinct action fingerprints observed."

        if len(fps) >= threshold and len(set(fps[:threshold])) == 1:
            is_stuck = True
            remedy = (
                f"STUCK DETECTED ({threshold} identical consecutive fingerprints '{fps[0]}'). "
                "Stop repeating the failing tool call. Check the latest open supervisor_node "
                "and switch to its `alternative_branch` or isolate a minimal reproduction."
            )
        elif len(fps) >= 4 and fps[0] == fps[2] and fps[1] == fps[3] and fps[0] != fps[1]:
            is_stuck = True
            remedy = (
                f"OSCILLATION DETECTED ('{fps[0]}' <-> '{fps[1]}'). "
                "Two mutually undoing actions are ping-ponging. Log a decision node and verify baseline assumptions."
            )

        return {
            "ok": True,
            "session_id": sid,
            "is_stuck": is_stuck,
            "remedy": remedy,
            "nodes": [dict(n) for n in nodes],
            "recent_fingerprints": [dict(s) for s in steps],
        }
    finally:
        conn.close()
