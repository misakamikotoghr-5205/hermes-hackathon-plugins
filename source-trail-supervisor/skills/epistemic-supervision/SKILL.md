---
name: epistemic-supervision
description: Anchor claims to exact Unicode source spans, enforce deterministic contradiction gates, and recover from stuck execution loops using causal decision nodes.
---

# Epistemic & Trajectory Supervision Workflow

Use this skill whenever you are synthesizing multi-source research, auditing policy compliance, or recovering a complex debugging session.

## 1. Exact-Span Citation Protocol (`source_trail_ingest` & `source_trail_verify`)

1. **Never paraphrase a quotation as an extractive claim.**
2. Compute zero-based Unicode code-point offsets `[start, end)` on each source document's `text` so that `source.text[start:end] == quote` holds character-for-character.
3. Call `source_trail_ingest` with your `sources` and `anchors`. If any offset or substring is misaligned, fix the span rather than guessing.
4. Before presenting conclusions, call `source_trail_verify`:
   - If `gate_status == "verified_clean"`, cite the `accepted_claims` with their `[start, end)` spans.
   - If `gate_status == "withheld_contradiction"`, **do not pick a winner silently**. Present the `disagreement_review_list` to the user and ask how to resolve the conflicting source positions.

## 2. Stuck-Session & Causal Node Protocol (`session_supervisor_node`)

1. Before attempting a risky fix or multi-step refactor, log a causal checkpoint:
   ```json
   {
     "action": "log_node",
     "node_title": "Fix parser offset boundary",
     "hypothesis": "Off-by-one in trailing newline handling",
     "evidence_ref": "tests/test_parser.py::test_trailing_lf",
     "alternative_branch": "Switch to splitlines(keepends=True) reconstruction",
     "outcome": "open"
   }
   ```
2. If a tool fails twice in a row or `/trail-supervise` reports `is_stuck: true`, stop repeating the same tool call immediately, run `session_supervisor_node({"action": "overview"})`, mark the current node `refuted`, and pivot to its `alternative_branch`.
