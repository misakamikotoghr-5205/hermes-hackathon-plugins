"""DelegationProvider implementation for claim-market-router."""

from __future__ import annotations

from typing import Any, Mapping

try:
    from agent.delegation_provider import DelegationProvider, DelegationRouteError
except ImportError:
    class DelegationRouteError(ValueError):
        """Fallback DelegationRouteError when tested standalone outside Hermes."""

    class DelegationProvider:  # type: ignore[no-redef]
        """Fallback DelegationProvider base class when tested standalone outside Hermes."""

        def settings(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
            backends = config.get("backends") if isinstance(config, Mapping) else None
            own = backends.get(self.name) if isinstance(backends, Mapping) else None
            return own if isinstance(own, Mapping) else {}

from .market import VALID_ROLES, run_claim_auction


class ClaimMarketDelegationProvider(DelegationProvider):
    """Market-based delegation provider (`delegation.backend: claim_market`)."""

    @property
    def name(self) -> str:
        return "claim_market"

    @property
    def display_name(self) -> str:
        return "Claim Market Router"

    @property
    def summary(self) -> str:
        return "Auctions each delegated task across candidate routes using capability fit, quota health, and shadow prices."

    def is_available(self) -> bool:
        return True

    def task_parameters(self, config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            "role_needed": {
                "type": "string",
                "enum": list(VALID_ROLES),
                "description": (
                    "Market role for this task: 'explorer' (cheap/fast discovery), "
                    "'implementer' (balanced coding/drafting), 'verifier' (independent review), "
                    "or 'finalizer' (high-reasoning synthesis)."
                ),
            },
            "complexity": {
                "type": "integer",
                "description": "Estimated task complexity from 1 (routine lookup) to 5 (deep architectural or formal proof).",
            },
            "max_cost_units": {
                "type": "number",
                "description": "Optional ceiling on relative route cost units for this subagent task.",
            },
        }

    def description(self, config: Mapping[str, Any]) -> str:
        return (
            "Set `role_needed` (explorer|implementer|verifier|finalizer) and `complexity` (1..5) "
            "per delegated task so the Claim Market Router can auction the work across candidate models."
        )

    def route_task(self, task: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
        own_settings = self.settings(config)
        candidates = own_settings.get("candidates") if isinstance(own_settings, Mapping) else None
        agreement_margin = float(own_settings.get("agreement_margin", 0.08)) if isinstance(own_settings, Mapping) else 0.08
        window_budget = int(own_settings.get("window_budget_tokens", 500000)) if isinstance(own_settings, Mapping) else 500000

        decision = run_claim_auction(
            goal=str(task.get("goal", "")),
            role_needed=str(task.get("role_needed") or "implementer"),
            complexity=int(task.get("complexity") or 3),
            max_cost_units=float(task["max_cost_units"]) if task.get("max_cost_units") is not None else None,
            candidates=candidates,
            agreement_margin=agreement_margin,
            window_budget_tokens=window_budget,
            record_receipt=True,
        )

        if not decision["feasible"] or not decision.get("winner"):
            raise DelegationRouteError(str(decision.get("infeasibility_report") or "No feasible route in claim market."))

        winner = decision["winner"]
        route: dict[str, Any] = {}
        for key in (
            "model",
            "provider",
            "base_url",
            "api_mode",
            "reasoning_effort",
            "service_tier",
            "fallback_providers",
            "request_overrides",
            "profile",
        ):
            if winner.get(key):
                route[key] = winner[key]

        route["label"] = (
            f"{winner['name']} [{decision['resolution_mode']}, conf={decision['confidence']:.2f}, "
            f"tier={winner.get('service_tier') or 'normal'}, verifier={decision['recommended_verifier']}]"
        )
        return route
