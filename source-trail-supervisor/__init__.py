"""Source Trail & Session Supervisor plugin for Hermes Agent.

Registers:
- Tools (`source_trail_ingest`, `source_trail_verify`, `session_supervisor_node`)
- Hooks (`on_session_start`, `post_tool_call`, `post_llm_call`)
- Bundled skill (`epistemic-supervision`)
- Slash command (`/trail-supervise`) and CLI command (`hermes trail-supervise`)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from . import schemas, tools
from .supervisor import compute_step_fingerprint, get_supervisor_overview, record_step_and_check_stuck

logger = logging.getLogger(__name__)


def _on_session_start(**kwargs: Any) -> None:
    session_id = str(kwargs.get("session_id") or "default")
    record_step_and_check_stuck(
        session_id=session_id,
        step_kind="session_start",
        fingerprint="session_init",
        detail="Session started",
    )


def _make_post_tool_hook(ctx: Any):
    def _on_post_tool_call(**kwargs: Any) -> None:
        try:
            tool_name = str(kwargs.get("tool_name") or "unknown_tool")
            args = kwargs.get("args")
            result = kwargs.get("result")
            session_id = str(kwargs.get("session_id") or kwargs.get("task_id") or "default")

            error_flag = False
            if isinstance(result, str) and ('"error"' in result or '"ok": false' in result.lower()):
                error_flag = True

            try:
                threshold = int(ctx.get_config("stuck_threshold", default=4))
            except Exception:
                threshold = 4

            fp = compute_step_fingerprint(tool_name, args, error_flag)
            record_step_and_check_stuck(
                session_id=session_id,
                step_kind=f"tool:{tool_name}",
                fingerprint=fp,
                detail=f"err={int(error_flag)}",
                stuck_threshold=threshold,
            )
        except Exception as exc:
            logger.debug("source-trail-supervisor post_tool_call error: %s", exc)

    return _on_post_tool_call


def _on_post_llm_call(**kwargs: Any) -> None:
    try:
        session_id = str(kwargs.get("session_id") or kwargs.get("task_id") or "default")
        model = str(kwargs.get("model") or "llm")
        record_step_and_check_stuck(
            session_id=session_id,
            step_kind="llm_turn",
            fingerprint=f"llm:{model[:24]}",
            detail=model,
        )
    except Exception as exc:
        logger.debug("source-trail-supervisor post_llm_call error: %s", exc)


def _handle_slash_command(raw_args: str) -> str:
    tokens = (raw_args or "").strip().split(maxsplit=1)
    sub = tokens[0].lower() if tokens else "overview"
    if sub == "verify" and len(tokens) > 1:
        return tools.source_trail_verify({"packet_id": tokens[1].strip()})
    return json.dumps(get_supervisor_overview(session_id="all"), ensure_ascii=False)


def _register_cli(parser: Any) -> None:
    sub = parser.add_subparsers(dest="subcommand", help="Source Trail & Session Supervisor commands")
    ov = sub.add_parser("overview", help="Show session progress fingerprints, stuck status, and decision nodes")
    ov.add_argument("--session", default="all", help="Session ID to filter (default: all)")
    vf = sub.add_parser("verify", help="Verify an ingested source packet and run the contradiction gate")
    vf.add_argument("packet_id", help="Packet ID")


def _run_cli(args: Any) -> int:
    sub = getattr(args, "subcommand", None) or "overview"
    if sub == "verify":
        out = tools.source_trail_verify({"packet_id": args.packet_id})
    else:
        session_id = getattr(args, "session", "all")
        out = json.dumps(get_supervisor_overview(session_id=session_id), ensure_ascii=False)
    print(json.dumps(json.loads(out), indent=2, ensure_ascii=False))
    return 0


def register(ctx: Any) -> None:
    """Register tools, hooks, bundled skill, and commands with Hermes."""
    ctx.register_tool(
        name="source_trail_ingest",
        toolset="source-trail-supervisor",
        schema=schemas.SOURCE_TRAIL_INGEST,
        handler=tools.source_trail_ingest,
    )
    ctx.register_tool(
        name="source_trail_verify",
        toolset="source-trail-supervisor",
        schema=schemas.SOURCE_TRAIL_VERIFY,
        handler=tools.source_trail_verify,
    )
    ctx.register_tool(
        name="session_supervisor_node",
        toolset="source-trail-supervisor",
        schema=schemas.SESSION_SUPERVISOR_NODE,
        handler=tools.session_supervisor_node,
    )

    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("post_tool_call", _make_post_tool_hook(ctx))
    ctx.register_hook("post_llm_call", _on_post_llm_call)

    # Register bundled skill if ctx supports register_skill
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.is_dir() and hasattr(ctx, "register_skill"):
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                try:
                    ctx.register_skill(child.name, skill_md)
                except Exception:
                    pass

    if hasattr(ctx, "register_command"):
        ctx.register_command(
            "trail-supervise",
            _handle_slash_command,
            description="Inspect stuck-loop progress fingerprints, decision nodes, or verify a source packet (/trail-supervise [overview|verify <packet_id>])",
        )

    if hasattr(ctx, "register_cli_command"):
        ctx.register_cli_command(
            "trail-supervise",
            help="Exact-span source verification and session progress supervision",
            setup_fn=_register_cli,
            handler_fn=_run_cli,
        )
