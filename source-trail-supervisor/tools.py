"""Tool handlers for source-trail-supervisor."""

from __future__ import annotations

import json
from typing import Any

from .supervisor import get_supervisor_overview, record_decision_node
from .trail import validate_and_ingest_packet, verify_selection_and_contradiction_gate


def source_trail_ingest(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        packet_id = str(args.get("packet_id") or "").strip()
        sources = args.get("sources") or []
        anchors = args.get("anchors") or []
        res = validate_and_ingest_packet(
            packet_id=packet_id,
            sources=sources,
            anchors=anchors,
            strict_quote_match=True,
        )
        return json.dumps(res, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"source_trail_ingest failed: {exc}"})


def source_trail_verify(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        packet_id = str(args.get("packet_id") or "").strip()
        selected = args.get("selected_anchor_ids")
        res = verify_selection_and_contradiction_gate(
            packet_id=packet_id,
            selected_anchor_ids=selected if isinstance(selected, list) else None,
        )
        return json.dumps(res, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"source_trail_verify failed: {exc}"})


def session_supervisor_node(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        action = str(args.get("action") or "overview").strip()
        session_id = str(kwargs.get("session_id") or kwargs.get("task_id") or args.get("session_id") or "default")

        if action == "log_node":
            title = str(args.get("node_title") or "").strip()
            if not title:
                return json.dumps({"ok": False, "error": "'node_title' is required when action='log_node'."})
            res = record_decision_node(
                session_id=session_id,
                node_title=title,
                hypothesis=str(args.get("hypothesis") or ""),
                evidence_ref=str(args.get("evidence_ref") or ""),
                alternative_branch=str(args.get("alternative_branch") or ""),
                outcome=str(args.get("outcome") or "open"),
            )
            return json.dumps(res, ensure_ascii=False)

        overview = get_supervisor_overview(session_id=session_id)
        return json.dumps(overview, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"session_supervisor_node failed: {exc}"})
