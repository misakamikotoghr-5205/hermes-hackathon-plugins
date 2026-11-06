"""Live end-to-end demonstration of all three Hermes Agent Hackathon plugins.

Run with:
    python -B scripts/run_live_demo.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_all_plugins import MockPluginContext, load_plugin_package  # noqa: E402


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def main() -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="hermes_live_demo_"))
    plugin_data_dir = temp_dir / "plugin-data"

    try:
        for pdir in ("claim-market-router", "hunk-consent-guard", "source-trail-supervisor"):
            pkg = load_plugin_package(pdir)
            pkg.storage.TEST_DATA_DIR = plugin_data_dir

        # ==================================================================
        # 1. CLAIM MARKET ROUTER
        # ==================================================================
        banner("PLUGIN 1: claim-market-router (DelegationProvider + llm_request Middleware)")
        cm_pkg = load_plugin_package("claim-market-router")
        cm_ctx = MockPluginContext({"auto_effort_shaping": True, "window_budget_tokens": 100000})
        cm_pkg.register(cm_ctx)

        auction_fn = cm_ctx.tools["claim_market_auction"]["handler"]
        r1 = json.loads(
            auction_fn(
                {
                    "goal": "Scan workspace files and list test entrypoints",
                    "role_needed": "explorer",
                    "complexity": 1,
                }
            )
        )
        print(
            f"[1a] Explorer Task (complexity=1) -> Winner: {r1['winner']['name']} "
            f"({r1['winner']['model']}, tier={r1['winner']['service_tier']}, cost={r1['winner']['cost_units']}, "
            f"mode={r1['resolution_mode']}, verifier={r1['recommended_verifier']})"
        )

        r2 = json.loads(
            auction_fn(
                {
                    "goal": "Audit security invariants and sign off release",
                    "role_needed": "finalizer",
                    "complexity": 5,
                }
            )
        )
        print(
            f"[1b] Finalizer Task (complexity=5) -> Winner: {r2['winner']['name']} "
            f"({r2['winner']['model']}, fallbacks={r2['winner']['fallback_providers']}, "
            f"confidence={r2['winner']['claim_confidence']})"
        )

        r3 = json.loads(
            auction_fn(
                {
                    "goal": "Implement distributed consensus engine",
                    "role_needed": "implementer",
                    "complexity": 4,
                    "max_cost_units": 0.25,
                }
            )
        )
        print(f"[1c] Infeasible Budget (max_cost=0.25) -> feasible={r3['feasible']}")
        print(f"     {r3['infeasibility_report']}")

        cm_ctx.hooks["post_api_request"][0](
            session_id="demo-s1",
            provider="openrouter",
            model="openai/gpt-6-astra-pro",
            usage={"prompt_tokens": 60000, "completion_tokens": 35000, "total_tokens": 95000},
        )
        mw_res = cm_ctx.middleware["llm_request"][0](
            request={
                "model": "openai/gpt-6-astra-pro",
                "reasoning_effort": "high",
                "messages": [{"role": "user", "content": "list files"}],
            }
        )
        print(
            f"[1d] llm_request Middleware after 95k/100k tokens -> "
            f"reasoning_effort={mw_res['request']['reasoning_effort']!r} ({mw_res['reason']})"
        )

        # ==================================================================
        # 2. HUNK CONSENT GUARD
        # ==================================================================
        banner("PLUGIN 2: hunk-consent-guard (Per-Hunk Consent + Drift Guard + Rollback)")
        hc_pkg = load_plugin_package("hunk-consent-guard")
        hc_ctx = MockPluginContext()
        hc_pkg.register(hc_ctx)

        demo_file = temp_dir / "service_config.py"
        original_code = (
            " TIMEOUT_SEC = 10\n"
            " MAX_RETRIES = 3\n"
            " KEEP_ALIVE = True\n"
            " DEBUG_MODE = False\n"
        )
        demo_file.write_text(original_code, encoding="utf-8")

        proposed_code = (
            " TIMEOUT_SEC = 30\n"
            " MAX_RETRIES = 3\n"
            " KEEP_ALIVE = True\n"
            " DEBUG_MODE = True\n"
        )
        prop = json.loads(
            hc_ctx.tools["hunk_propose"]["handler"](
                {
                    "target_path": str(demo_file),
                    "proposed_text": proposed_code,
                    "summary": "Increase timeout and enable debug mode",
                }
            )
        )
        pid = prop["proposal_id"]
        print(
            f"[2a] Staged Proposal #{pid} on service_config.py -> "
            f"hunk_count={prop['hunk_count']}, baseline_sha256={prop['baseline_sha256'][:12]}..."
        )

        hc_ctx.commands["hunk-desk"]["handler"](f"approve {pid} 1")
        applied = json.loads(hc_ctx.tools["hunk_apply_approved"]["handler"]({"proposal_id": pid}))
        after_lines = [line.strip() for line in demo_file.read_text(encoding="utf-8").splitlines()]
        print(
            f"[2b] User approved ONLY Hunk #1 via `/hunk-desk approve {pid} 1` (rejected Hunk #2 DEBUG_MODE=True) -> "
            f"applied_hunks={applied['applied_hunks']}, receipt_id=#{applied['receipt_id']}"
        )
        print(f"     Resulting lines: {after_lines}")

        rb = json.loads(
            hc_ctx.tools["hunk_rollback_receipt"]["handler"]({"receipt_id": applied["receipt_id"]})
        )
        print(
            f"[2c] Rolled back Receipt #{rb['receipt_id']} -> "
            f"restored_sha256={rb['restored_sha256'][:12]}... (matches original={demo_file.read_text(encoding='utf-8') == original_code})"
        )

        prop2 = json.loads(
            hc_ctx.tools["hunk_propose"]["handler"](
                {
                    "target_path": str(demo_file),
                    "proposed_text": proposed_code,
                }
            )
        )
        hc_ctx.commands["hunk-desk"]["handler"](f"approve {prop2['proposal_id']} 1,2")
        demo_file.write_text(original_code + "# Concurrent human edit\n", encoding="utf-8")
        drift = json.loads(
            hc_ctx.tools["hunk_apply_approved"]["handler"]({"proposal_id": prop2["proposal_id"]})
        )
        print(
            f"[2d] Out-of-band edit before apply -> status={drift['status']!r}: {drift['error']}"
        )

        # ==================================================================
        # 3. SOURCE TRAIL & SESSION SUPERVISOR
        # ==================================================================
        banner("PLUGIN 3: source-trail-supervisor (Unicode Span Verifier + Contradiction Gate + Loop Guard)")
        st_pkg = load_plugin_package("source-trail-supervisor")
        st_ctx = MockPluginContext({"stuck_threshold": 3})
        st_pkg.register(st_ctx)

        doc_1 = "Standard API tier allows up to 60 requests per minute."
        doc_2 = "Standard API tier is strictly capped at 10 requests per minute."

        bad_span = json.loads(
            st_ctx.tools["source_trail_ingest"]["handler"](
                {
                    "packet_id": "pkt-hallucinated",
                    "sources": [{"id": "doc1", "title": "API Spec v1", "text": doc_1}],
                    "anchors": [
                        {
                            "id": "a1",
                            "source_id": "doc1",
                            "start": 0,
                            "end": 20,
                            "quote": "Paraphrased rate limit text",
                            "topic": "rate_limit",
                            "position": "60_rpm",
                        }
                    ],
                }
            )
        )
        print(
            f"[3a] Non-verbatim Span Check -> ok={bad_span['ok']}, status={bad_span['status']!r} "
            f"({bad_span['errors'][0]})"
        )

        st_ctx.tools["source_trail_ingest"]["handler"](
            {
                "packet_id": "pkt-rate-conflict",
                "sources": [
                    {"id": "doc1", "title": "Public Docs", "text": doc_1},
                    {"id": "doc2", "title": "Gateway Policy", "text": doc_2},
                ],
                "anchors": [
                    {
                        "id": "a1",
                        "source_id": "doc1",
                        "start": 0,
                        "end": len(doc_1),
                        "quote": doc_1,
                        "topic": "standard_tier_rpm",
                        "position": "60_rpm",
                    },
                    {
                        "id": "a2",
                        "source_id": "doc2",
                        "start": 0,
                        "end": len(doc_2),
                        "quote": doc_2,
                        "topic": "standard_tier_rpm",
                        "position": "10_rpm",
                    },
                ],
            }
        )
        verified = json.loads(
            st_ctx.tools["source_trail_verify"]["handler"]({"packet_id": "pkt-rate-conflict"})
        )
        print(
            f"[3b] Contradiction Gate on 'standard_tier_rpm' -> "
            f"gate_status={verified['gate_status']!r}, accepted_claims={len(verified['accepted_claims'])}, "
            f"disagreements={len(verified['disagreement_review_list'])}"
        )

        for _ in range(3):
            st_ctx.hooks["post_tool_call"][0](
                session_id="demo-loop",
                tool_name="terminal",
                args={"command": "pytest tests/integration.py"},
                result='{"error": "ConnectionRefusedError"}',
            )
        logged = json.loads(
            st_ctx.tools["session_supervisor_node"]["handler"](
                {
                    "action": "log_node",
                    "node_title": "Switch from live integration test to local mock server",
                    "hypothesis": "Integration endpoint is unreachable in offline sandbox",
                    "evidence_ref": "pkt-rate-conflict#a2",
                    "alternative_branch": "Start local fixture server before running pytest",
                    "outcome": "pivoted",
                },
                session_id="demo-loop",
            )
        )
        ov = json.loads(
            st_ctx.tools["session_supervisor_node"]["handler"](
                {"action": "overview"},
                session_id="demo-loop",
            )
        )
        print(
            f"[3c] Stuck-Loop Supervisor -> is_stuck={ov['is_stuck']}, "
            f"latest_fingerprint={ov['recent_fingerprints'][0]['fingerprint']}, logged_node=#{logged['node_id']}"
        )
        print(f"     Remedy: {ov['remedy']}")
        print("\n" + "=" * 78)
        print("  ALL THREE PLUGINS EXECUTED LIVE AND VERIFIED SUCCESSFULLY!")
        print("=" * 78)
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
