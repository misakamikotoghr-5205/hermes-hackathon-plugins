# Hunk Consent Guard (`hunk-consent-guard`)

Per-hunk patch staging, **SHA-256 baseline-drift approval revocation**, and **drift-checked rollback receipts** for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Derived from [`patch-review-desk`](https://github.com/misakamikotoghr-5205/patch-review-desk) and [`cart-consent-paypal`](https://github.com/misakamikotoghr-5205/cart-consent-paypal).

## Core Safety Guarantees

1. **User-Only Granular Per-Hunk Consent (`hunk_propose`, `hunk_review_status`, `/hunk-desk`):**
   Stage a multi-hunk file edit without touching the working tree. Model-facing tools (`hunk_propose`, `hunk_review_status`) cannot approve hunks; approval comes exclusively from the user via `/hunk-desk approve <proposal_id> 1,3` or `hermes hunk-desk approve <proposal_id> 1,3`, and `hunk_apply_approved` also escalates through Hermes's `pre_tool_call` approval gate.
2. **Core File-Safety Enforcement & `write_file` Dispatch:**
   Relative paths are resolved against the terminal cwd (`resolve_agent_cwd()`), every read/stage check enforces `agent.file_safety.get_read_block_error` and `get_write_denied_error`, and all file writes dispatch through `ctx.dispatch_tool("write_file", ...)`.
3. **Automatic Baseline-Drift Revocation:**
   Every proposal pins the target file's `baseline_sha256`. If the file on disk is modified out-of-band before `hunk_apply_approved` runs, `hunk-consent-guard` detects the SHA-256 drift, revokes all approvals (`status: "drifted_revoked"`), and refuses to overwrite the file.
4. **Durable Rollback Receipts (`tool_execution` Middleware & `hunk_rollback_receipt`):**
   Every applied hunk proposal—and every `write_file`/`patch` call wrapped by `tool_execution` middleware—records a receipt with `before_sha256`, `after_sha256`, unified diff, and text snapshots in `<HERMES_HOME>/plugin-data/hunk-consent-guard/data.db`. Rolling back a receipt verifies that the current file still matches `after_sha256` before restoring `before_text`, so later edits are never clobbered.

## Installation

```bash
hermes plugins install misakamikotoghr-5205/hermes-hackathon-plugins --subdir hunk-consent-guard
hermes plugins enable hunk-consent-guard
```

## Slash & CLI Commands

```text
/hunk-desk list
/hunk-desk status 1
/hunk-desk approve 1 1,3
/hunk-desk apply 1
/hunk-desk rollback 1
```

## Disclosure (Catalog Rule 13)

- **Filesystem Access:** Reads target workspace files during `write_file`/`patch` tool execution and explicit `hunk_propose` / `hunk_apply_approved` / `hunk_rollback_receipt` calls; writes target files only when `hunk_apply_approved` or `hunk_rollback_receipt` is explicitly invoked.
- **Storage:** Persists file snapshots (up to `max_snapshot_kb`, default 256 KB) and SHA-256 receipts in `<HERMES_HOME>/plugin-data/hunk-consent-guard/data.db`.
- **Approvals & Network:** Never alters or bypasses Hermes's built-in approval prompts; makes no network calls and spawns no subprocesses.
