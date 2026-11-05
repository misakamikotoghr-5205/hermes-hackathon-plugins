# Claim Market Router (`claim-market-router`)

A cost-aware, quota-aware **Claim Market Delegation Provider** (`delegation.backend: claim_market`) and optional **`llm_request` reasoning-effort shaper** for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Derived from [`Cost-aware-claim-based-multi-model-AI-orchestrator`](https://github.com/misakamikotoghr-5205/Cost-aware-claim-based-multi-model-AI-orchestrator) (**MISAKA AGENT**) and [`watt-window`](https://github.com/misakamikotoghr-5205/watt-window).

## Core Idea

> **Cheap models explore. Strong models decide. Expensive models finalize.**

Instead of static tier mapping, `claim-market-router` treats subagent delegation (`delegate_task`) as a **claim market**:
1. **Task Cards:** Each delegated task specifies `role_needed` (`explorer`, `implementer`, `verifier`, `finalizer`), `complexity` (`1..5`), and an optional `max_cost_units` ceiling.
2. **Claim Synthesis & Shadow Pricing:** Candidate model routes synthesize claims from capability fit and rolling-window quota health minus a convex **shadow price** ($\lambda_i$) that rises as the route's token budget approaches exhaustion:
   $$\text{confidence}_i = 0.60 \cdot \text{capability\_fit}_i + 0.40 \cdot \text{quota\_health}_i - \lambda_i(\text{utilization})$$
3. **Agreement vs. Weighted Voting:** When the pure utility score and highest-confidence claim agree within `agreement_margin`, the route is assigned directly; otherwise, candidate routes resolve the disagreement via **weighted voting** and nominate the strongest independent route as `recommended_verifier`.
4. **Explainable Infeasibility & Sensitivity Reports:** If `max_cost_units` or exhausted quota filters out all routes, the router raises a `DelegationRouteError` explaining the exact budget relaxation needed.

## Installation & Configuration

```bash
hermes plugins install misakamikotoghr-5205/hermes-hackathon-plugins --subdir claim-market-router
hermes plugins enable claim-market-router
hermes config set delegation.backend claim_market
```

Example `config.yaml` setup:
```yaml
delegation:
  backend: claim_market
  backends:
    claim_market:
      agreement_margin: 0.08
      window_budget_tokens: 500000
      candidates:
        - name: scout-fast
          provider: openrouter
          model: google/gemini-2.5-flash
          reasoning_effort: low
          cost_units: 1.0
          quality_tier: 2
          preferred_roles: [explorer, implementer]
          vote_weight: 1.0
          window_quota_tokens: 300000
        - name: builder-balanced
          provider: openrouter
          model: anthropic/claude-sonnet-4
          reasoning_effort: medium
          cost_units: 3.5
          quality_tier: 4
          preferred_roles: [implementer, verifier]
          vote_weight: 1.4
          window_quota_tokens: 200000
        - name: arbiter-frontier
          provider: openrouter
          model: openai/gpt-5
          reasoning_effort: high
          cost_units: 8.0
          quality_tier: 5
          preferred_roles: [verifier, finalizer]
          vote_weight: 1.8
          window_quota_tokens: 100000
```

## Surfaces Provided

- **Delegation Provider:** `claim_market` (`ctx.register_delegation_provider`)
- **Tools:** `claim_market_auction`, `claim_market_ledger`
- **Hook:** `post_llm_call` (tracks token usage in `<HERMES_HOME>/plugin-data/claim-market-router/data.db`)
- **Middleware:** `llm_request` (no-op by default; when `auto_effort_shaping: true`, shapes `reasoning_effort` on exploratory turns when shadow price is elevated)
- **Commands:** `/claim-market [status|auction <goal>|reset]` and `hermes claim-market [status|auction|reset]`

## Disclosure (Catalog Rule 13)

- **Network & Subprocesses:** None. All claim synthesis, weighted voting, and sensitivity calculations are deterministic and local.
- **Credentials:** Reads no credentials or provider secret files.
- **Storage:** Writes token-usage counts and auction receipts to `<HERMES_HOME>/plugin-data/claim-market-router/data.db` via `plugins.plugin_storage.plugin_db`.
- **Middleware Behavior:** `llm_request` middleware is disabled by default (`auto_effort_shaping: false`); when enabled by the user, it adjusts only `reasoning_effort` on outgoing requests when window shadow price exceeds `0.20`.
