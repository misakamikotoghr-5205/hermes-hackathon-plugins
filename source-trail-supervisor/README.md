# Source Trail & Session Supervisor (`source-trail-supervisor`)

Exact zero-based **Unicode code-point span citation verifier**, **deterministic contradiction gate**, and **progress-fingerprint stuck-session supervisor** for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Derived from [`source-trail-otari`](https://github.com/misakamikotoghr-5205/source-trail-otari), [`volc-casedesk`](https://github.com/misakamikotoghr-5205/volc-casedesk), [`codex-session-supervisor`](https://github.com/misakamikotoghr-5205/codex-session-supervisor), and [`deadlock-manor`](https://github.com/misakamikotoghr-5205/deadlock-manor).

## Capabilities

1. **Exact Unicode Span Verification (`source_trail_ingest`):**
   Verifies that every registered citation anchor `[start, end)` on `source_id` strictly equals the verbatim `quote` without fuzzy relocation or paraphrase, pinning the packet with a SHA-256 digest.
2. **Deterministic Contradiction & Policy-Conflict Gate (`source_trail_verify`):**
   Checks all valid anchors per `topic` (filtering to the latest `effective_date` when policy dates are provided). If conflicting `position` labels exist on the same topic, all unilateral claims are withheld (`gate_status: "withheld_contradiction"`) and a `disagreement_review_list` is returned.
3. **Progress Fingerprinting & Causal Decision Nodes (`session_supervisor_node` & Hooks):**
   Monitors `post_tool_call` and `post_llm_call` events to compute rolling action/error fingerprints. Detects `identical_repeat` and `abab_oscillation` loops and logs recoverable causal decision nodes (`hypothesis`, `evidence_ref`, `alternative_branch`).
4. **Bundled Skill (`skills/epistemic-supervision/SKILL.md`):**
   Guides the agent through verbatim span anchoring, contradiction handling, and loop recovery.

## Installation

```bash
hermes plugins install misakamikotoghr-5205/hermes-hackathon-plugins --subdir source-trail-supervisor
hermes plugins enable source-trail-supervisor
```

## Disclosure (Catalog Rule 13)

- **Observed Events:** Observes tool names, target path/query keys, error flags, and turn counts via `on_session_start`, `post_tool_call`, and `post_llm_call` hooks.
- **Storage:** Stores user-ingested source packets, verified anchors, progress fingerprints, and causal decision nodes in `<HERMES_HOME>/plugin-data/source-trail-supervisor/data.db`.
- **Network & Credentials:** Makes no network requests, spawns no subprocesses, and reads no credentials.
