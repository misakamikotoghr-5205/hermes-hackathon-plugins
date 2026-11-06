"""Tool handlers for hunk-consent-guard."""

from __future__ import annotations

import json
from typing import Any

from .engine import (
    apply_approved_proposal,
    check_and_update_Approvals,
    create_proposal,
    list_receipts_and_proposals,
    rollback_from_receipt,
)


def hunk_propose(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        target_path = str(args.get("target_path") or "").strip()
        proposed_text = args.get("proposed_text")
        if not target_path or proposed_text is None:
            return json.dumps({"ok": False, "error": "Both 'target_path' and 'proposed_text' are required."})

        task_id = str(kwargs.get("task_id") or "default")
        res = create_proposal(
            target_path=target_path,
            proposed_text=str(proposed_text),
            summary=str(args.get("summary") or ""),
            task_id=task_id,
        )
        return json.dumps(res, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"hunk_propose failed: {exc}"})


def hunk_review_status(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        proposal_id = args.get("proposal_id")
        if proposal_id is None:
            overview = list_receipts_and_proposals(limit=15)
            return json.dumps({"ok": True, **overview}, ensure_ascii=False)

        # Model-facing tool is strictly read-only inspection (plus baseline-drift revocation).
        # Hunk approval comes exclusively from the user via /hunk-desk approve or hermes hunk-desk approve.
        res = check_and_update_Approvals(
            proposal_id=int(proposal_id),
            approve_hunks=None,
            revoke_all=False,
        )
        return json.dumps(res, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"hunk_review_status failed: {exc}"})


def hunk_apply_approved(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        proposal_id = args.get("proposal_id")
        if proposal_id is None:
            return json.dumps({"ok": False, "error": "Parameter 'proposal_id' is required."})
        res = apply_approved_proposal(int(proposal_id))
        return json.dumps(res, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"hunk_apply_approved failed: {exc}"})


def hunk_rollback_receipt(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        receipt_id = args.get("receipt_id")
        if receipt_id is None:
            return json.dumps({"ok": False, "error": "Parameter 'receipt_id' is required."})
        res = rollback_from_receipt(int(receipt_id))
        return json.dumps(res, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"hunk_rollback_receipt failed: {exc}"})
