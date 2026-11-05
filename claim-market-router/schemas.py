"""Tool schemas for claim-market-router."""

from __future__ import annotations

CLAIM_MARKET_AUCTION = {
    "name": "claim_market_auction",
    "description": (
        "Run a deterministic cost-aware, quota-aware claim market auction across candidate "
        "models for a task card. Evaluates capability fit, rolling-window quota health, and "
        "shadow prices, resolving disagreements via weighted voting and returning the winning "
        "route, recommended verifier, and sensitivity analysis if constraints are infeasible."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "One-sentence summary of the task to route or delegate.",
            },
            "role_needed": {
                "type": "string",
                "enum": ["explorer", "implementer", "verifier", "finalizer"],
                "description": "Target role: explorer (cheap/fast), implementer (balanced), verifier (review), finalizer (deep synthesis).",
            },
            "complexity": {
                "type": "integer",
                "description": "Task complexity on a 1..5 scale (1 = simple lookup, 5 = critical architecture/math).",
            },
            "max_cost_units": {
                "type": "number",
                "description": "Optional maximum relative cost units allowed for this task.",
            },
        },
        "required": ["goal", "role_needed", "complexity"],
    },
}

CLAIM_MARKET_LEDGER = {
    "name": "claim_market_ledger",
    "description": (
        "Inspect the Claim Market Router rolling-window token usage ledger, current route "
        "shadow prices, and recent subagent auction receipts."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "recent_auctions", "reset"],
                "description": "Query rolling usage status, list recent auction receipts, or reset local ledger stats.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of recent auction receipts to return (1..50).",
            },
        },
        "required": ["action"],
    },
}
