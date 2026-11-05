"""Tool handlers for claim-market-router."""

from __future__ import annotations

import json
from typing import Any

from .market import DEFAULT_CANDIDATES, compute_shadow_price, run_claim_auction
from .storage import clear_ledger, get_window_usage, list_recent_auctions


def claim_market_auction(args: dict[str, Any], **kwargs: Any) -> str:
    """Run a claim market auction and return a JSON string."""
    try:
        goal = str(args.get("goal") or "").strip()
        if not goal:
            return json.dumps({"ok": False, "error": "Parameter 'goal' is required."})

        role_needed = str(args.get("role_needed") or "implementer").strip()
        complexity = int(args.get("complexity") or 3)
        max_cost_raw = args.get("max_cost_units")
        max_cost_units = float(max_cost_raw) if max_cost_raw is not None else None

        result = run_claim_auction(
            goal=goal,
            role_needed=role_needed,
            complexity=complexity,
            max_cost_units=max_cost_units,
            record_receipt=True,
        )
        return json.dumps({"ok": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"claim_market_auction failed: {exc}"})


def claim_market_ledger(args: dict[str, Any], **kwargs: Any) -> str:
    """Inspect or reset the claim-market-router SQLite ledger."""
    try:
        action = str(args.get("action") or "status").strip()
        limit = int(args.get("limit") or 10)

        if action == "reset":
            cleared = clear_ledger()
            return json.dumps({"ok": True, "action": "reset", **cleared})

        if action == "recent_auctions":
            auctions = list_recent_auctions(limit=limit)
            return json.dumps({"ok": True, "action": "recent_auctions", "auctions": auctions})

        usage = get_window_usage()
        by_model = usage.get("by_model", {})
        route_health = []
        for c in DEFAULT_CANDIDATES:
            key = f"{c['provider']}/{c['model']}".strip("/")
            used = int((by_model.get(key) or {}).get("total_tokens", 0))
            quota = int(c.get("window_quota_tokens", 300000))
            route_health.append(
                {
                    "name": c["name"],
                    "route": key,
                    "used_tokens": used,
                    "window_quota_tokens": quota,
                    "quota_health": round(max(0.0, 1.0 - used / float(max(1, quota))), 4),
                    "shadow_price": compute_shadow_price(used, quota),
                }
            )

        return json.dumps(
            {
                "ok": True,
                "action": "status",
                "window_usage": usage,
                "route_health": route_health,
                "recent_auctions": list_recent_auctions(limit=5),
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"claim_market_ledger failed: {exc}"})
