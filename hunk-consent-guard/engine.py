"""Per-hunk staging, SHA-256 baseline-drift invalidation, and rollback receipt engine.

Adapted from:
- misakamikotoghr-5205/patch-review-desk (per-hunk approval, baseline drift revocation, rollback receipts)
- misakamikotoghr-5205/cart-consent-paypal (field/item-level consent & revision invalidation)
"""

from __future__ import annotations

import difflib
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Sequence

from .storage import get_db

_ACTIVE_CTX: Any = None
_IN_INTERNAL_WRITE: bool = False

_FALLBACK_BLOCKED_NAMES = frozenset(
    {
        ".env",
        "credentials.json",
        "id_rsa",
        "id_ed25519",
        "authorized_keys",
        ".netrc",
        ".npmrc",
        ".pypirc",
    }
)


def bind_plugin_context(ctx: Any) -> None:
    """Bind the active Hermes PluginContext so file writes dispatch through write_file."""
    global _ACTIVE_CTX
    _ACTIVE_CTX = ctx


def is_in_internal_write() -> bool:
    """Return True while hunk-consent-guard is dispatching an internal write_file call."""
    return _IN_INTERNAL_WRITE


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_workspace_path(raw_path: str, task_id: str = "default") -> Path:
    """Resolve relative paths against the terminal cwd, matching Hermes write_file semantics."""
    try:
        from tools.file_tools_paths import _resolve_path_for_task  # type: ignore

        return Path(str(_resolve_path_for_task(raw_path, task_id)))
    except Exception:
        pass

    expanded = Path(raw_path).expanduser()
    if not expanded.is_absolute():
        base_cwd: Path | None = None
        try:
            from agent.runtime_cwd import resolve_agent_cwd  # type: ignore

            base_cwd = Path(resolve_agent_cwd())
        except Exception:
            base_cwd = Path.cwd()
        expanded = base_cwd / expanded
    return expanded.resolve()


def _fallback_safety_error(candidate: str, *, check_read: bool, check_write: bool) -> str | None:
    """Fallback denylist check used only when running outside the Hermes runtime."""
    raw = str(candidate or "").strip()
    if raw.startswith("\\\\?\\") or raw.startswith("\\??\\"):
        return f"Blocked NT namespace path: {raw}"
    try:
        p = Path(raw)
        name = p.name.lower()
        parts_lower = {part.lower() for part in p.parts}
    except Exception:
        return f"Invalid file path: {raw}"

    if name in _FALLBACK_BLOCKED_NAMES or (name.startswith(".env.") and name != ".env.example"):
        action = "Read/write" if (check_read and check_write) else ("Read" if check_read else "Write")
        return f"{action} denied by safety policy for protected file: {p.name}"
    if ".ssh" in parts_lower or ".aws" in parts_lower or ".gnupg" in parts_lower:
        return f"Access denied for protected credential directory in path: {raw}"
    return None


def check_file_safety(
    raw_path: str,
    resolved_path: Path | str | None = None,
    *,
    check_read: bool = True,
    check_write: bool = True,
) -> str | None:
    """Check Hermes core read-blocklist and write-denylist on both raw and resolved paths."""
    candidates: list[str] = [str(raw_path)]
    if resolved_path is not None and str(resolved_path) not in candidates:
        candidates.append(str(resolved_path))

    try:
        from agent.file_safety import get_read_block_error, get_write_denied_error  # type: ignore

        for cand in candidates:
            if check_read:
                read_err = get_read_block_error(cand)
                if read_err:
                    return str(read_err)
            if check_write:
                write_err = get_write_denied_error(cand)
                if write_err:
                    return str(write_err)
        return None
    except ImportError:
        for cand in candidates:
            err = _fallback_safety_error(cand, check_read=check_read, check_write=check_write)
            if err:
                return err
        return None


def _write_file_via_ctx(
    target_path: Path,
    content: str,
    *,
    ctx: Any = None,
) -> str | None:
    """Write file contents exclusively through ctx.dispatch_tool('write_file', ...)."""
    global _IN_INTERNAL_WRITE

    safety_err = check_file_safety(str(target_path), target_path, check_read=False, check_write=True)
    if safety_err:
        return safety_err

    active_ctx = ctx or _ACTIVE_CTX
    if active_ctx is None or not hasattr(active_ctx, "dispatch_tool"):
        return "Write refused: no active Hermes PluginContext.dispatch_tool available."

    _IN_INTERNAL_WRITE = True
    try:
        raw_res = active_ctx.dispatch_tool(
            "write_file",
            {"path": str(target_path), "content": content},
        )
    except Exception as exc:
        return f"write_file dispatch failed: {exc}"
    finally:
        _IN_INTERNAL_WRITE = False

    if isinstance(raw_res, dict):
        if raw_res.get("error"):
            return str(raw_res["error"])
        return None

    if isinstance(raw_res, str) and raw_res.strip():
        try:
            parsed = json.loads(raw_res)
            if isinstance(parsed, dict) and parsed.get("error"):
                return str(parsed["error"])
        except Exception:
            pass
    return None


def compute_hunks(old_text: str, new_text: str, target_path: str = "file") -> list[dict[str, Any]]:
    """Decompose the difference between old_text and new_text into non-overlapping line hunks."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    hunks: list[dict[str, Any]] = []
    hunk_index = 1
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        before_chunk = "".join(old_lines[i1:i2])
        after_chunk = "".join(new_lines[j1:j2])
        preview_diff = "".join(
            difflib.unified_diff(
                old_lines[i1:i2],
                new_lines[j1:j2],
                fromfile=f"a/{Path(target_path).name}:{i1 + 1}",
                tofile=f"b/{Path(target_path).name}:{j1 + 1}",
                n=0,
            )
        )
        hunks.append(
            {
                "hunk_id": hunk_index,
                "op": tag,
                "old_start": i1,
                "old_end": i2,
                "new_start": j1,
                "new_end": j2,
                "before_chunk": before_chunk,
                "after_chunk": after_chunk,
                "diff_preview": preview_diff.strip(),
            }
        )
        hunk_index += 1
    return hunks


def apply_selected_hunks(old_text: str, hunks: Sequence[dict[str, Any]], approved_ids: set[int]) -> str:
    """Reconstruct text by applying only the hunks whose hunk_id is in approved_ids."""
    old_lines = old_text.splitlines(keepends=True)
    out_parts: list[str] = []
    cursor = 0

    for h in sorted(hunks, key=lambda x: (int(x["old_start"]), int(x["old_end"]))):
        start = int(h["old_start"])
        end = int(h["old_end"])
        if start > cursor:
            out_parts.append("".join(old_lines[cursor:start]))
        if int(h["hunk_id"]) in approved_ids:
            out_parts.append(str(h["after_chunk"]))
        else:
            out_parts.append("".join(old_lines[start:end]))
        cursor = end

    if cursor < len(old_lines):
        out_parts.append("".join(old_lines[cursor:]))

    return "".join(out_parts)


def create_proposal(
    *,
    target_path: str,
    proposed_text: str,
    summary: str = "",
    task_id: str = "default",
) -> dict[str, Any]:
    raw_err = check_file_safety(target_path, None, check_read=True, check_write=True)
    if raw_err:
        return {"ok": False, "error": raw_err}

    path_obj = resolve_workspace_path(target_path, task_id=task_id)
    safety_err = check_file_safety(target_path, path_obj, check_read=True, check_write=True)
    if safety_err:
        return {"ok": False, "error": safety_err}

    if not path_obj.exists():
        baseline_text = ""
    else:
        baseline_text = path_obj.read_text(encoding="utf-8")

    baseline_hash = sha256_text(baseline_text)
    hunks = compute_hunks(baseline_text, proposed_text, target_path=str(path_obj))
    if not hunks:
        return {
            "ok": False,
            "error": "Proposed text is identical to current file baseline; no hunks generated.",
        }

    approved_ids: list[int] = []
    conn = get_db()
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO hunk_proposals
                    (ts, target_path, summary, baseline_sha256, baseline_text,
                     hunks_json, approved_hunks_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    str(path_obj),
                    summary,
                    baseline_hash,
                    baseline_text,
                    json.dumps(hunks, ensure_ascii=False),
                    json.dumps(approved_ids),
                    "pending",
                ),
            )
            proposal_id = int(cur.lastrowid or 0)
    finally:
        conn.close()

    return {
        "ok": True,
        "proposal_id": proposal_id,
        "target_path": str(path_obj),
        "baseline_sha256": baseline_hash,
        "hunk_count": len(hunks),
        "approved_hunks": approved_ids,
        "status": "pending",
        "hunks": [
            {
                "hunk_id": h["hunk_id"],
                "op": h["op"],
                "old_range": [h["old_start"] + 1, h["old_end"]],
                "diff_preview": h["diff_preview"],
            }
            for h in hunks
        ],
    }


def check_and_update_Approvals(
    *,
    proposal_id: int,
    approve_hunks: Sequence[int] | None = None,
    revoke_all: bool = False,
) -> dict[str, Any]:
    """Inspect a proposal, verify its baseline has not drifted on disk, and (when called by user CLI/slash commands) update approved hunks."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM hunk_proposals WHERE id = ?", (int(proposal_id),)).fetchone()
        if not row:
            return {"ok": False, "error": f"Proposal #{proposal_id} not found."}

        target_path = Path(row["target_path"])
        safety_err = check_file_safety(str(target_path), target_path, check_read=True, check_write=True)
        if safety_err:
            return {"ok": False, "error": safety_err}

        current_text = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        current_hash = sha256_text(current_text)
        baseline_hash = str(row["baseline_sha256"])
        hunks = json.loads(row["hunks_json"])
        valid_ids = {int(h["hunk_id"]) for h in hunks}

        # Baseline drift check: if file changed on disk since proposal creation, revoke all approvals!
        if current_hash != baseline_hash and row["status"] != "applied":
            with conn:
                conn.execute(
                    """
                    UPDATE hunk_proposals
                    SET approved_hunks_json = '[]', status = 'drifted_revoked'
                    WHERE id = ?
                    """,
                    (int(proposal_id),),
                )
            return {
                "ok": False,
                "proposal_id": int(proposal_id),
                "target_path": str(target_path),
                "status": "drifted_revoked",
                "baseline_sha256": baseline_hash,
                "current_sha256": current_hash,
                "approved_hunks": [],
                "error": (
                    "Baseline drift detected: the file on disk was modified after this proposal was staged. "
                    "All hunk approvals have been automatically revoked."
                ),
            }

        approved = [int(x) for x in json.loads(row["approved_hunks_json"])]
        status = str(row["status"])

        if revoke_all and status != "applied":
            approved = []
            status = "pending"
            with conn:
                conn.execute(
                    "UPDATE hunk_proposals SET approved_hunks_json = '[]', status = 'pending' WHERE id = ?",
                    (int(proposal_id),),
                )
        elif approve_hunks is not None and status != "applied":
            requested = [int(x) for x in approve_hunks]
            unknown = [x for x in requested if x not in valid_ids]
            if unknown:
                return {"ok": False, "error": f"Unknown hunk IDs for proposal #{proposal_id}: {unknown}"}
            approved = sorted(set(requested))
            status = "approved" if approved else "pending"
            with conn:
                conn.execute(
                    "UPDATE hunk_proposals SET approved_hunks_json = ?, status = ? WHERE id = ?",
                    (json.dumps(approved), status, int(proposal_id)),
                )

        return {
            "ok": True,
            "proposal_id": int(proposal_id),
            "target_path": str(target_path),
            "summary": row["summary"],
            "status": status,
            "baseline_sha256": baseline_hash,
            "current_sha256": current_hash,
            "baseline_intact": current_hash == baseline_hash,
            "approved_hunks": approved,
            "hunk_count": len(hunks),
            "hunks": [
                {
                    "hunk_id": h["hunk_id"],
                    "approved": int(h["hunk_id"]) in set(approved),
                    "op": h["op"],
                    "diff_preview": h["diff_preview"],
                }
                for h in hunks
            ],
        }
    finally:
        conn.close()


check_and_update_approvals = check_and_update_Approvals


def apply_approved_proposal(
    proposal_id: int,
    max_snapshot_kb: int = 256,
    *,
    ctx: Any = None,
) -> dict[str, Any]:
    """Apply the approved hunks of a proposal if and only if the baseline SHA-256 is unchanged,
    dispatching the write through Hermes write_file and persisting an atomic rollback receipt.
    """
    status_check = check_and_update_Approvals(proposal_id=proposal_id)
    if not status_check.get("ok"):
        return status_check

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM hunk_proposals WHERE id = ?", (int(proposal_id),)).fetchone()
        if not row:
            return {"ok": False, "error": f"Proposal #{proposal_id} not found."}
        if row["status"] == "applied":
            return {"ok": False, "error": f"Proposal #{proposal_id} was already applied."}

        approved = {int(x) for x in json.loads(row["approved_hunks_json"])}
        if not approved:
            return {
                "ok": False,
                "error": (
                    f"Proposal #{proposal_id} has no approved hunks. "
                    f"User approval is required via `/hunk-desk approve {proposal_id} 1` or `hermes hunk-desk approve {proposal_id} 1`."
                ),
            }

        hunks = json.loads(row["hunks_json"])
        baseline_text = str(row["baseline_text"])
        new_text = apply_selected_hunks(baseline_text, hunks, approved)
        after_hash = sha256_text(new_text)

        target_path = Path(row["target_path"])
        write_err = _write_file_via_ctx(target_path, new_text, ctx=ctx)
        if write_err:
            return {"ok": False, "error": write_err}

        diff_str = "".join(
            difflib.unified_diff(
                baseline_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{target_path.name}",
                tofile=f"b/{target_path.name}",
            )
        )
        max_bytes = max(1, int(max_snapshot_kb)) * 1024
        store_before = baseline_text if len(baseline_text.encode("utf-8")) <= max_bytes else None
        store_after = new_text if len(new_text.encode("utf-8")) <= max_bytes else None

        with conn:
            conn.execute(
                "UPDATE hunk_proposals SET status = 'applied' WHERE id = ?",
                (int(proposal_id),),
            )
            cur = conn.execute(
                """
                INSERT INTO rollback_receipts
                    (ts, source_kind, proposal_id, target_path, before_sha256, after_sha256,
                     before_text, after_text, unified_diff, rolled_back)
                VALUES (?, 'hunk_proposal', ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    time.time(),
                    int(proposal_id),
                    str(target_path),
                    str(row["baseline_sha256"]),
                    after_hash,
                    store_before,
                    store_after,
                    diff_str,
                ),
            )
            receipt_id = int(cur.lastrowid or 0)

        return {
            "ok": True,
            "proposal_id": int(proposal_id),
            "receipt_id": receipt_id,
            "target_path": str(target_path),
            "applied_hunks": sorted(approved),
            "total_hunks": len(hunks),
            "before_sha256": str(row["baseline_sha256"]),
            "after_sha256": after_hash,
            "unified_diff": diff_str,
        }
    finally:
        conn.close()


def record_direct_write_receipt(
    *,
    source_kind: str,
    target_path: str,
    before_text: str,
    after_text: str,
    max_snapshot_kb: int = 256,
    task_id: str = "default",
) -> int | None:
    """Record a rollback receipt from tool_execution middleware when an allowed file changes."""
    before_hash = sha256_text(before_text)
    after_hash = sha256_text(after_text)
    if before_hash == after_hash:
        return None

    path_obj = resolve_workspace_path(target_path, task_id=task_id)
    if check_file_safety(target_path, path_obj, check_read=True, check_write=True):
        return None

    diff_str = "".join(
        difflib.unified_diff(
            before_text.splitlines(keepends=True),
            after_text.splitlines(keepends=True),
            fromfile=f"a/{path_obj.name}",
            tofile=f"b/{path_obj.name}",
        )
    )
    max_bytes = max(1, int(max_snapshot_kb)) * 1024
    store_before = before_text if len(before_text.encode("utf-8")) <= max_bytes else None
    store_after = after_text if len(after_text.encode("utf-8")) <= max_bytes else None

    conn = get_db()
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO rollback_receipts
                    (ts, source_kind, proposal_id, target_path, before_sha256, after_sha256,
                     before_text, after_text, unified_diff, rolled_back)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    time.time(),
                    source_kind,
                    str(path_obj),
                    before_hash,
                    after_hash,
                    store_before,
                    store_after,
                    diff_str,
                ),
            )
            return int(cur.lastrowid or 0)
    finally:
        conn.close()


def rollback_from_receipt(receipt_id: int, *, ctx: Any = None) -> dict[str, Any]:
    """Restore a file using a persisted receipt if and only if current file hash matches after_sha256."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM rollback_receipts WHERE id = ?", (int(receipt_id),)).fetchone()
        if not row:
            return {"ok": False, "error": f"Receipt #{receipt_id} not found."}
        if int(row["rolled_back"]):
            return {"ok": False, "error": f"Receipt #{receipt_id} has already been rolled back."}
        if row["before_text"] is None:
            return {
                "ok": False,
                "error": f"Receipt #{receipt_id} stores hashes only (file exceeded max_snapshot_kb).",
            }

        target_path = Path(row["target_path"])
        safety_err = check_file_safety(str(target_path), target_path, check_read=True, check_write=True)
        if safety_err:
            return {"ok": False, "error": safety_err}

        current_text = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        current_hash = sha256_text(current_text)
        expected_after_hash = str(row["after_sha256"])

        if current_hash != expected_after_hash:
            return {
                "ok": False,
                "receipt_id": int(receipt_id),
                "target_path": str(target_path),
                "expected_after_sha256": expected_after_hash,
                "current_sha256": current_hash,
                "error": (
                    "Rollback refused due to post-apply drift: the file was modified after this receipt "
                    "was recorded. Rolling back would overwrite newer changes."
                ),
            }

        before_text = str(row["before_text"])
        write_err = _write_file_via_ctx(target_path, before_text, ctx=ctx)
        if write_err:
            return {"ok": False, "error": write_err}

        with conn:
            conn.execute("UPDATE rollback_receipts SET rolled_back = 1 WHERE id = ?", (int(receipt_id),))

        return {
            "ok": True,
            "receipt_id": int(receipt_id),
            "target_path": str(target_path),
            "restored_sha256": str(row["before_sha256"]),
        }
    finally:
        conn.close()


def list_receipts_and_proposals(limit: int = 10) -> dict[str, Any]:
    conn = get_db()
    try:
        lim = max(1, min(int(limit), 50))
        proposals = conn.execute(
            """
            SELECT id, ts, target_path, summary, baseline_sha256, approved_hunks_json, status
            FROM hunk_proposals
            ORDER BY id DESC
            LIMIT ?
            """,
            (lim,),
        ).fetchall()
        receipts = conn.execute(
            """
            SELECT id, ts, source_kind, proposal_id, target_path, before_sha256, after_sha256, rolled_back
            FROM rollback_receipts
            ORDER BY id DESC
            LIMIT ?
            """,
            (lim,),
        ).fetchall()
        return {
            "proposals": [dict(p) for p in proposals],
            "receipts": [dict(r) for r in receipts],
        }
    finally:
        conn.close()
