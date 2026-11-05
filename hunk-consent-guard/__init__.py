"""Hunk Consent Guard plugin for Hermes Agent.

Registers:
- Tools (`hunk_propose`, `hunk_review_status`, `hunk_apply_approved`, `hunk_rollback_receipt`)
- Hook (`post_tool_call`)
- Middleware (`tool_execution`)
- Slash command (`/hunk-desk`) and CLI command (`hermes hunk-desk`)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from . import schemas, tools
from .engine import record_direct_write_receipt

logger = logging.getLogger(__name__)

_WRITE_TOOLS = frozenset({"write_file", "patch", "edit_file"})
_last_tool_events: list[dict[str, Any]] = []


def _extract_target_path(args: dict[str, Any]) -> str | None:
    for key in ("path", "file_path", "target_path", "Path", "filename"):
        val = args.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _make_tool_execution_middleware(ctx: Any):
    """Wrap file-mutating tool executions to record before/after SHA-256 rollback receipts."""

    def _on_tool_execution(**kwargs: Any) -> Any:
        tool_name = str(kwargs.get("tool_name") or "")
        args = kwargs.get("args")
        next_call = kwargs.get("next_call")
        if not callable(next_call):
            return None

        try:
            record_all = bool(ctx.get_config("record_all_writes", default=True))
            max_kb = int(ctx.get_config("max_snapshot_kb", default=256))
        except Exception:
            record_all = True
            max_kb = 256

        target_path_str = _extract_target_path(args) if (record_all and tool_name in _WRITE_TOOLS and isinstance(args, dict)) else None
        before_text: str | None = None
        resolved_path: Path | None = None

        if target_path_str:
            try:
                resolved_path = Path(target_path_str).expanduser().resolve()
                before_text = resolved_path.read_text(encoding="utf-8") if resolved_path.exists() else ""
            except Exception:
                before_text = None

        result = next_call(args)

        if resolved_path is not None and before_text is not None:
            try:
                after_text = resolved_path.read_text(encoding="utf-8") if resolved_path.exists() else ""
                record_direct_write_receipt(
                    source_kind=f"middleware:{tool_name}",
                    target_path=str(resolved_path),
                    before_text=before_text,
                    after_text=after_text,
                    max_snapshot_kb=max_kb,
                )
            except Exception as exc:
                logger.debug("hunk-consent-guard receipt capture skipped: %s", exc)

        return result

    return _on_tool_execution


def _on_post_tool_call(**kwargs: Any) -> None:
    tool_name = str(kwargs.get("tool_name") or "")
    if tool_name in _WRITE_TOOLS or tool_name.startswith("hunk_"):
        _last_tool_events.append(
            {
                "tool_name": tool_name,
                "task_id": str(kwargs.get("task_id") or ""),
            }
        )
        if len(_last_tool_events) > 100:
            _last_tool_events.pop(0)


def _handle_slash_command(raw_args: str) -> str:
    tokens = (raw_args or "").strip().split()
    if not tokens or tokens[0] == "list":
        return tools.hunk_review_status({})
    cmd = tokens[0].lower()
    if cmd == "status" and len(tokens) >= 2:
        return tools.hunk_review_status({"proposal_id": int(tokens[1])})
    if cmd == "approve" and len(tokens) >= 3:
        pid = int(tokens[1])
        hunk_ids = [int(x.strip()) for x in tokens[2].split(",") if x.strip()]
        return tools.hunk_review_status({"proposal_id": pid, "approve_hunks": hunk_ids})
    if cmd == "apply" and len(tokens) >= 2:
        return tools.hunk_apply_approved({"proposal_id": int(tokens[1])})
    if cmd == "rollback" and len(tokens) >= 2:
        return tools.hunk_rollback_receipt({"receipt_id": int(tokens[1])})
    return json.dumps(
        {
            "ok": False,
            "usage": "/hunk-desk [list | status <id> | approve <id> <h1,h2> | apply <id> | rollback <receipt_id>]",
        }
    )


def _register_cli(parser: Any) -> None:
    sub = parser.add_subparsers(dest="subcommand", help="Hunk Consent Guard subcommands")
    sub.add_parser("list", help="List recent staged proposals and rollback receipts")
    st = sub.add_parser("status", help="Inspect a proposal and verify its baseline hash")
    st.add_argument("proposal_id", type=int)
    ap = sub.add_parser("approve", help="Approve comma-separated hunk IDs on a proposal")
    ap.add_argument("proposal_id", type=int)
    ap.add_argument("hunks", help="Comma-separated 1-based hunk IDs (e.g. 1,3)")
    apply_p = sub.add_parser("apply", help="Apply approved hunks on a proposal")
    apply_p.add_argument("proposal_id", type=int)
    rb = sub.add_parser("rollback", help="Roll back a file modification by receipt ID")
    rb.add_argument("receipt_id", type=int)


def _run_cli(args: Any) -> int:
    sub = getattr(args, "subcommand", None) or "list"
    if sub == "status":
        out = tools.hunk_review_status({"proposal_id": args.proposal_id})
    elif sub == "approve":
        ids = [int(x.strip()) for x in str(args.hunks).split(",") if x.strip()]
        out = tools.hunk_review_status({"proposal_id": args.proposal_id, "approve_hunks": ids})
    elif sub == "apply":
        out = tools.hunk_apply_approved({"proposal_id": args.proposal_id})
    elif sub == "rollback":
        out = tools.hunk_rollback_receipt({"receipt_id": args.receipt_id})
    else:
        out = tools.hunk_review_status({})
    print(json.dumps(json.loads(out), indent=2, ensure_ascii=False))
    return 0


def register(ctx: Any) -> None:
    """Register hunk-consent-guard tools, hooks, middleware, and commands."""
    ctx.register_tool(
        name="hunk_propose",
        toolset="hunk-consent-guard",
        schema=schemas.HUNK_PROPOSE,
        handler=tools.hunk_propose,
    )
    ctx.register_tool(
        name="hunk_review_status",
        toolset="hunk-consent-guard",
        schema=schemas.HUNK_REVIEW_STATUS,
        handler=tools.hunk_review_status,
    )
    ctx.register_tool(
        name="hunk_apply_approved",
        toolset="hunk-consent-guard",
        schema=schemas.HUNK_APPLY_APPROVED,
        handler=tools.hunk_apply_approved,
    )
    ctx.register_tool(
        name="hunk_rollback_receipt",
        toolset="hunk-consent-guard",
        schema=schemas.HUNK_ROLLBACK_RECEIPT,
        handler=tools.hunk_rollback_receipt,
    )

    ctx.register_hook("post_tool_call", _on_post_tool_call)
    ctx.register_middleware("tool_execution", _make_tool_execution_middleware(ctx))

    if hasattr(ctx, "register_command"):
        ctx.register_command(
            "hunk-desk",
            _handle_slash_command,
            description="Review, approve, apply, or roll back staged file hunks (/hunk-desk [list|status|approve|apply|rollback])",
        )

    if hasattr(ctx, "register_cli_command"):
        ctx.register_cli_command(
            "hunk-desk",
            help="Per-hunk patch consent, drift verification, and rollback receipts",
            setup_fn=_register_cli,
            handler_fn=_run_cli,
        )
