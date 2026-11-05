# Hermes Agent Hackathon Plugins (`misakamikotoghr-5205`)

Three standalone, zero-dependency Python plugins for [Hermes Agent](https://github.com/NousResearch/hermes-agent) built for the **Nous Research Hermes Agent Plugin Hackathon**, adapting core algorithms and safety contracts from [`misakamikotoghr-5205`](https://github.com/misakamikotoghr-5205)'s open-source repositories.

| Plugin | Category | Subdirectory | Hermes Extension Surfaces | Derived From |
| :--- | :--- | :--- | :--- | :--- |
| **[`claim-market-router`](./claim-market-router)** | `models` | `claim-market-router` | `DelegationProvider` (`claim_market`), `llm_request` middleware, `post_llm_call` hook, 2 tools, `/claim-market`, `hermes claim-market` | [`Cost-aware-claim-based-multi-model-AI-orchestrator`](https://github.com/misakamikotoghr-5205/Cost-aware-claim-based-multi-model-AI-orchestrator), [`watt-window`](https://github.com/misakamikotoghr-5205/watt-window) |
| **[`hunk-consent-guard`](./hunk-consent-guard)** | `tools` | `hunk-consent-guard` | `tool_execution` middleware, `post_tool_call` hook, 4 tools, `/hunk-desk`, `hermes hunk-desk` | [`patch-review-desk`](https://github.com/misakamikotoghr-5205/patch-review-desk), [`cart-consent-paypal`](https://github.com/misakamikotoghr-5205/cart-consent-paypal) |
| **[`source-trail-supervisor`](./source-trail-supervisor)** | `general` | `source-trail-supervisor` | `on_session_start` / `post_tool_call` / `post_llm_call` hooks, 3 tools, bundled `epistemic-supervision` Skill, `/trail-supervise`, `hermes trail-supervise` | [`source-trail-otari`](https://github.com/misakamikotoghr-5205/source-trail-otari), [`volc-casedesk`](https://github.com/misakamikotoghr-5205/volc-casedesk), [`codex-session-supervisor`](https://github.com/misakamikotoghr-5205/codex-session-supervisor) |

## Quick Verification

Python 3.11+, zero third-party runtime dependencies:

```bash
python -m unittest discover -s tests -v
python scripts/validate_plugins.py
```

## Catalog Entry Templates

Ready-to-submit catalog files for `NousResearch/hermes-agent/plugin-catalog/` are located in [`plugin-catalog/`](./plugin-catalog):
- [`plugin-catalog/claim-market-router.yaml`](./plugin-catalog/claim-market-router.yaml)
- [`plugin-catalog/hunk-consent-guard.yaml`](./plugin-catalog/hunk-consent-guard.yaml)
- [`plugin-catalog/source-trail-supervisor.yaml`](./plugin-catalog/source-trail-supervisor.yaml)
