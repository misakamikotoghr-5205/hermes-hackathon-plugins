"""Claim Market Router plugin for Hermes Agent.

Registers:
- DelegationProvider (`claim_market`)
- Tools (`claim_market_auction`, `claim_market_ledger`)
- Hook (`post_llm_call`)
- Middleware (`llm_request`)
- Slash command (`/claim-market`) and CLI command (`hermes claim-market`)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from . import schemas, tools
from .market import compute_shadow_price
from .provider import ClaimMarketDelegationProvider
from .storage import get_window_usage, record_token_usage

logger = logging.getLogger(__name__)


def _on_post_llm_call(**kwargs: Any) -> None:
    """Observer hook: record token usage from completed LLM calls into the local SQLite ledger."""
    try:
        usage = kwargs.get("usage") or {}
        if not isinstance(usage, dict):
            return
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
        if total_tokens <= 0:
            return
        record_token_usage(
            session_id=str(kwargs.get("session_id") or kwargs.get("task_id") or ""),
            provider=str(kwargs.get("provider") or ""),
            model=str(kwargs.get("model") or ""),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
    except Exception as exc:
        logger.debug("claim-market-router post_llm_call error: %s", exc)


def _make_llm_request_middleware(ctx: Any):
    """Build the llm_request middleware closure bound to this plugin's config."""

    def _on_llm_request(**kwargs: Any) -> dict[str, Any]:
        request = kwargs.get("request")
        if not isinstance(request, dict):
            return {"request": request}

        try:
            auto_shape = bool(ctx.get_config("auto_effort_shaping", default=False))
        except Exception:
            auto_shape = False

        if not auto_shape:
            return {"request": request}

        try:
            window_budget = int(ctx.get_config("window_budget_tokens", default=500000))
        except Exception:
            window_budget = 500000

        usage = get_window_usage()
        total_used = int(usage.get("total_window_tokens", 0))
        shadow = compute_shadow_price(total_used, window_budget)

        updated = dict(request)
        messages = updated.get("messages") or []
        turn_count = len(messages) if isinstance(messages, list) else 0

        # When shadow price is high (>0.20) on early exploratory turns, conserve quota with 'low' effort
        if shadow >= 0.20 and turn_count <= 4 and updated.get("reasoning_effort") in (None, "high", "medium"):
            updated["reasoning_effort"] = "low"
            return {
                "request": updated,
                "source": "claim-market-router",
                "reason": f"shadow_price={shadow:.3f} on exploratory turn ({turn_count} msgs) -> reasoning_effort=low",
            }
        return {"request": updated}

    return _on_llm_request


def _handle_slash_command(raw_args: str) -> str:
    parts = (raw_args or "").strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else "status"
    if sub == "auction":
        goal = parts[1] if len(parts) > 1 else "General implementation task"
        return tools.claim_market_auction({"goal": goal, "role_needed": "implementer", "complexity": 3})
    if sub == "reset":
        return tools.claim_market_ledger({"action": "reset"})
    return tools.claim_market_ledger({"action": "status"})


def _register_cli(parser: Any) -> None:
    subparsers = parser.add_subparsers(dest="subcommand", help="Claim Market Router subcommands")
    subparsers.add_parser("status", help="Show rolling token usage and route shadow prices")
    sim = subparsers.add_parser("auction", help="Simulate a claim market auction for a task")
    sim.add_argument("goal", help="Task description")
    sim.add_argument("--role", default="implementer", choices=["explorer", "implementer", "verifier", "finalizer"])
    sim.add_argument("--complexity", type=int, default=3)
    sim.add_argument("--max-cost", type=float, default=None)
    subparsers.add_parser("reset", help="Clear local usage and auction ledger")


def _run_cli(args: Any) -> int:
    sub = getattr(args, "subcommand", None) or "status"
    if sub == "auction":
        out = tools.claim_market_auction(
            {
                "goal": args.goal,
                "role_needed": args.role,
                "complexity": args.complexity,
                "max_cost_units": args.max_cost,
            }
        )
    elif sub == "reset":
        out = tools.claim_market_ledger({"action": "reset"})
    else:
        out = tools.claim_market_ledger({"action": "status"})
    print(json.dumps(json.loads(out), indent=2, ensure_ascii=False))
    return 0


def register(ctx: Any) -> None:
    """Register tools, hooks, middleware, delegation provider, and commands with Hermes."""
    ctx.register_tool(
        name="claim_market_auction",
        toolset="claim-market-router",
        schema=schemas.CLAIM_MARKET_AUCTION,
        handler=tools.claim_market_auction,
    )
    ctx.register_tool(
        name="claim_market_ledger",
        toolset="claim-market-router",
        schema=schemas.CLAIM_MARKET_LEDGER,
        handler=tools.claim_market_ledger,
    )
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_hook("post_api_request", _on_post_llm_call)
    ctx.register_middleware("llm_request", _make_llm_request_middleware(ctx))

    if hasattr(ctx, "register_delegation_provider"):
        ctx.register_delegation_provider(ClaimMarketDelegationProvider())

    if hasattr(ctx, "register_command"):
        ctx.register_command(
            "claim-market",
            _handle_slash_command,
            description="Inspect Claim Market quota shadow prices or simulate a task auction (/claim-market [status|auction <goal>|reset])",
        )

    if hasattr(ctx, "register_cli_command"):
        ctx.register_cli_command(
            "claim-market",
            help="Cost-aware, quota-aware claim market router utilities",
            setup_fn=_register_cli,
            handler_fn=_run_cli,
        )
