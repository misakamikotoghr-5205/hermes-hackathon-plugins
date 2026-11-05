"""Deterministic cost-aware, quota-aware claim market and weighted-voting engine.

Adapted from:
- misakamikotoghr-5205/Cost-aware-claim-based-multi-model-AI-orchestrator
- misakamikotoghr-5205/watt-window (infeasibility & sensitivity explanations)
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .storage import get_window_usage, record_auction_receipt

VALID_ROLES = ("explorer", "implementer", "verifier", "finalizer")

DEFAULT_CANDIDATES: list[dict[str, Any]] = [
    {
        "name": "scout-fast",
        "provider": "openrouter",
        "model": "google/gemini-2.5-flash",
        "reasoning_effort": "low",
        "cost_units": 1.0,
        "quality_tier": 2,
        "preferred_roles": ["explorer", "implementer"],
        "vote_weight": 1.0,
        "window_quota_tokens": 300000,
    },
    {
        "name": "builder-balanced",
        "provider": "openrouter",
        "model": "anthropic/claude-sonnet-4",
        "reasoning_effort": "medium",
        "cost_units": 3.5,
        "quality_tier": 4,
        "preferred_roles": ["implementer", "verifier"],
        "vote_weight": 1.4,
        "window_quota_tokens": 200000,
    },
    {
        "name": "arbiter-frontier",
        "provider": "openrouter",
        "model": "openai/gpt-5",
        "reasoning_effort": "high",
        "cost_units": 8.0,
        "quality_tier": 5,
        "preferred_roles": ["verifier", "finalizer"],
        "vote_weight": 1.8,
        "window_quota_tokens": 100000,
    },
]

# Ideal quality tier per (role_needed, complexity)
_ROLE_MIN_QUALITY = {
    "explorer": 1,
    "implementer": 2,
    "verifier": 3,
    "finalizer": 4,
}


def compute_shadow_price(used_tokens: int, quota_tokens: int) -> float:
    """Convex shadow price penalty as a candidate route approaches window exhaustion."""
    if quota_tokens <= 0:
        return 0.0
    utilization = min(1.5, max(0.0, used_tokens / float(quota_tokens)))
    if utilization < 0.5:
        return round(0.05 * utilization, 4)
    if utilization < 0.85:
        return round(0.025 + 0.35 * (utilization - 0.5), 4)
    return round(0.1475 + 0.90 * (utilization - 0.85), 4)


def compute_capability_fit(
    candidate: Mapping[str, Any],
    role_needed: str,
    complexity: int,
) -> float:
    """Deterministic capability fit in [0.0, 1.0]."""
    quality = float(candidate.get("quality_tier", 3))
    preferred = list(candidate.get("preferred_roles") or ["implementer"])
    min_q = max(_ROLE_MIN_QUALITY.get(role_needed, 2), min(5, int(complexity)))

    role_bonus = 0.22 if role_needed in preferred else 0.0
    # Penalize under-qualified models heavily and over-qualified expensive models mildly on simple tasks
    if quality < min_q:
        gap_penalty = 0.28 * (min_q - quality)
        base_fit = max(0.1, 0.78 - gap_penalty)
    else:
        overkill = max(0.0, quality - max(min_q, complexity))
        # Cheap models explore; expensive models shouldn't waste quota on complexity=1 exploration
        overkill_penalty = 0.09 * overkill if role_needed == "explorer" else 0.03 * overkill
        base_fit = min(1.0, 0.78 + 0.05 * (quality - min_q) - overkill_penalty)

    return round(min(1.0, max(0.05, base_fit + role_bonus)), 4)


def run_claim_auction(
    *,
    goal: str,
    role_needed: str = "implementer",
    complexity: int = 3,
    max_cost_units: float | None = None,
    candidates: Sequence[Mapping[str, Any]] | None = None,
    agreement_margin: float = 0.08,
    window_budget_tokens: int = 500000,
    record_receipt: bool = True,
) -> dict[str, Any]:
    """Run a deterministic claim market auction across candidate routes.

    Returns a dictionary containing:
    - feasible (bool)
    - winner (dict) or None
    - recommended_verifier (str)
    - resolution_mode ('direct_agreement' | 'weighted_voting' | 'infeasible')
    - claims (list of synthesized claim cards)
    - sensitivity (dict explaining budget/quota constraints)
    """
    role = role_needed if role_needed in VALID_ROLES else "implementer"
    comp = max(1, min(5, int(complexity or 3)))
    pool = list(candidates) if candidates else list(DEFAULT_CANDIDATES)

    usage_snapshot = get_window_usage()
    by_model = usage_snapshot.get("by_model", {})

    # 1. Filter by hard cost constraint & build infeasibility sensitivity if needed
    feasible_pool: list[dict[str, Any]] = []
    rejected_reasons: list[dict[str, Any]] = []

    for raw_c in pool:
        c = dict(raw_c)
        cost = float(c.get("cost_units", 1.0))
        model_key = f"{c.get('provider', '')}/{c.get('model', '')}".strip("/")
        used_tokens = int(
            (by_model.get(model_key) or by_model.get(str(c.get("model", ""))) or {}).get("total_tokens", 0)
        )
        quota_tokens = int(c.get("window_quota_tokens") or window_budget_tokens or 500000)

        if max_cost_units is not None and cost > float(max_cost_units):
            rejected_reasons.append(
                {
                    "candidate": c.get("name", model_key),
                    "reason": "cost_ceiling_exceeded",
                    "candidate_cost_units": cost,
                    "max_cost_units": float(max_cost_units),
                    "relaxation_needed": round(cost - float(max_cost_units), 3),
                }
            )
            continue

        if quota_tokens > 0 and used_tokens >= quota_tokens:
            rejected_reasons.append(
                {
                    "candidate": c.get("name", model_key),
                    "reason": "window_quota_exhausted",
                    "used_tokens": used_tokens,
                    "window_quota_tokens": quota_tokens,
                }
            )
            continue

        c["_used_tokens"] = used_tokens
        c["_quota_tokens"] = quota_tokens
        feasible_pool.append(c)

    if not feasible_pool:
        min_cost_relax = min(
            (r["candidate_cost_units"] for r in rejected_reasons if "candidate_cost_units" in r),
            default=None,
        )
        msg_parts = [
            f"Claim Market Infeasible for role={role!r}, complexity={comp}: all {len(pool)} candidate routes were filtered out."
        ]
        if min_cost_relax is not None and max_cost_units is not None:
            msg_parts.append(
                f"Sensitivity: raise `max_cost_units` from {max_cost_units} to at least {min_cost_relax} "
                f"(+{round(min_cost_relax - float(max_cost_units), 2)} units) to unlock the cheapest route."
            )
        else:
            msg_parts.append("Sensitivity: reset or increase `window_budget_tokens` in claim-market-router settings.")
        return {
            "feasible": False,
            "winner": None,
            "recommended_verifier": "",
            "resolution_mode": "infeasible",
            "confidence": 0.0,
            "infeasibility_report": " ".join(msg_parts),
            "rejected_candidates": rejected_reasons,
            "claims": [],
        }

    # 2. Synthesize claims and initial pure-utility scores
    claims: list[dict[str, Any]] = []
    for c in feasible_pool:
        name = str(c.get("name") or c.get("model") or "route")
        cost = float(c.get("cost_units", 1.0))
        used_tokens = int(c["_used_tokens"])
        quota_tokens = int(c["_quota_tokens"])

        cap_fit = compute_capability_fit(c, role, comp)
        quota_health = round(max(0.0, 1.0 - (used_tokens / float(max(1, quota_tokens)))), 4)
        shadow_price = compute_shadow_price(used_tokens, quota_tokens)

        # Claim confidence formula from MISAKA Agent: 0.6 * capability_fit + 0.4 * quota_health - shadow_price
        claim_confidence = round(max(0.01, min(1.0, 0.60 * cap_fit + 0.40 * quota_health - shadow_price)), 4)

        # Initial cost-aware utility score penalizes raw cost more strongly on low-complexity tasks
        cost_weight = 0.06 if comp <= 2 else (0.035 if comp == 3 else 0.015)
        initial_score = round(cap_fit - cost_weight * cost - shadow_price, 4)

        claims.append(
            {
                "name": name,
                "provider": c.get("provider", ""),
                "model": c.get("model", ""),
                "reasoning_effort": c.get("reasoning_effort", ""),
                "profile": c.get("profile", ""),
                "cost_units": cost,
                "quality_tier": int(c.get("quality_tier", 3)),
                "capability_fit": cap_fit,
                "quota_health": quota_health,
                "shadow_price": shadow_price,
                "claim_confidence": claim_confidence,
                "initial_score": initial_score,
                "vote_weight": float(c.get("vote_weight", 1.0)),
            }
        )

    by_initial = sorted(claims, key=lambda x: (x["initial_score"], x["claim_confidence"]), reverse=True)
    by_claim = sorted(claims, key=lambda x: (x["claim_confidence"], x["initial_score"]), reverse=True)

    top_initial = by_initial[0]
    top_claim = by_claim[0]

    # 3. Agreement vs. Weighted Voting
    score_gap = abs(top_initial["claim_confidence"] - top_claim["claim_confidence"])
    if top_initial["name"] == top_claim["name"] or score_gap <= float(agreement_margin):
        winner = top_claim if top_claim["claim_confidence"] >= top_initial["claim_confidence"] else top_initial
        resolution_mode = "direct_agreement"
    else:
        # Weighted voting across all candidate agents
        vote_totals: dict[str, float] = {c["name"]: 0.0 for c in claims}
        for voter in claims:
            w = voter["vote_weight"]
            # Each voter distributes weight to top two candidates by combined (cap_fit + claim_confidence - 0.5*shadow_price)
            ranked = sorted(
                claims,
                key=lambda target: (
                    0.55 * target["capability_fit"]
                    + 0.45 * target["claim_confidence"]
                    - 0.25 * target["shadow_price"]
                ),
                reverse=True,
            )
            vote_totals[ranked[0]["name"]] = round(vote_totals[ranked[0]["name"]] + 0.7 * w, 4)
            if len(ranked) > 1:
                vote_totals[ranked[1]["name"]] = round(vote_totals[ranked[1]["name"]] + 0.3 * w, 4)

        for c in claims:
            c["weighted_votes"] = vote_totals[c["name"]]

        winner = max(claims, key=lambda c: (c.get("weighted_votes", 0.0), c["claim_confidence"]))
        resolution_mode = "weighted_voting"

    # Recommend the strongest *other* route as verifier
    other_verifiers = sorted(
        [c for c in claims if c["name"] != winner["name"]],
        key=lambda c: (c["quality_tier"], c["claim_confidence"]),
        reverse=True,
    )
    recommended_verifier = other_verifiers[0]["name"] if other_verifiers else winner["name"]

    result = {
        "feasible": True,
        "goal_summary": (goal or "")[:160],
        "role_needed": role,
        "complexity": comp,
        "winner": winner,
        "recommended_verifier": recommended_verifier,
        "resolution_mode": resolution_mode,
        "confidence": winner["claim_confidence"],
        "claims": by_claim,
        "rejected_candidates": rejected_reasons,
    }

    if record_receipt:
        receipt_id = record_auction_receipt(
            goal_summary=goal or "subagent task",
            role_needed=role,
            complexity=comp,
            winner_name=winner["name"],
            winner_model=f"{winner['provider']}/{winner['model']}".strip("/"),
            resolution_mode=resolution_mode,
            confidence=winner["claim_confidence"],
            verifier_name=recommended_verifier,
            payload_json=json.dumps(result, ensure_ascii=False),
        )
        result["receipt_id"] = receipt_id

    return result
