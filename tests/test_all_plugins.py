"""Comprehensive unit and Hermes-contract tests for all three hackathon plugins."""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_plugin_package(plugin_dir_name: str):
    """Load a hyphenated plugin directory as a synthetic package just like Hermes PluginManager."""
    plugin_path = REPO_ROOT / plugin_dir_name
    pkg_name = f"hermes_plugin_{plugin_dir_name.replace('-', '_')}"
    if pkg_name in sys.modules:
        return sys.modules[pkg_name]

    spec = importlib.util.spec_from_file_location(
        pkg_name,
        plugin_path / "__init__.py",
        submodule_search_locations=[str(plugin_path)],
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = module
    spec.loader.exec_module(module)
    return module


class MockPluginContext:
    """Mock Hermes PluginContext capturing all registered capabilities."""

    def __init__(self, settings: dict[str, Any] | None = None):
        self.tools: dict[str, dict[str, Any]] = {}
        self.hooks: dict[str, list[Any]] = {}
        self.middleware: dict[str, list[Any]] = {}
        self.delegation_providers: list[Any] = []
        self.commands: dict[str, dict[str, Any]] = {}
        self.cli_commands: dict[str, dict[str, Any]] = {}
        self.skills: dict[str, str] = {}
        self.settings: dict[str, Any] = dict(settings or {})
        self.dispatched_tools: list[tuple[str, dict[str, Any]]] = []

    def dispatch_tool(self, tool_name: str, args: dict[str, Any], **kwargs: Any) -> str:
        self.dispatched_tools.append((tool_name, dict(args)))
        if tool_name == "write_file":
            target = Path(str(args["path"]))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(args["content"]), encoding="utf-8")
            return json.dumps({"ok": True, "path": str(target)})
        return json.dumps({"ok": True})

    def register_tool(self, *, name: str, toolset: str, schema: dict[str, Any], handler: Any, **kwargs: Any) -> None:
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler}

    def register_hook(self, hook_name: str, callback: Any) -> None:
        self.hooks.setdefault(hook_name, []).append(callback)

    def register_middleware(self, kind: str, callback: Any) -> None:
        self.middleware.setdefault(kind, []).append(callback)

    def register_delegation_provider(self, provider: Any) -> None:
        self.delegation_providers.append(provider)

    def register_command(self, name: str, handler: Any, description: str = "") -> None:
        self.commands[name] = {"handler": handler, "description": description}

    def register_cli_command(
        self,
        name: str,
        help: str = "",
        setup_fn: Any = None,
        handler_fn: Any = None,
        description: str = "",
    ) -> None:
        self.cli_commands[name] = {
            "help": help,
            "setup_fn": setup_fn,
            "handler_fn": handler_fn,
            "description": description,
        }

    def register_skill(self, name: str, path: Any) -> None:
        self.skills[name] = str(path)

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        self.settings[key] = value


class TestHermesHackathonPlugins(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="hermes_hackathon_test_"))
        self.plugin_data_dir = self.temp_dir / "plugin-data"
        for pdir in ("claim-market-router", "hunk-consent-guard", "source-trail-supervisor"):
            pkg = load_plugin_package(pdir)
            pkg.storage.TEST_DATA_DIR = self.plugin_data_dir

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _assert_handler_contract(self, fn: Any) -> None:
        sig = inspect.signature(fn)
        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        self.assertTrue(has_var_kw, f"Handler {fn} must accept **kwargs for Hermes forward compatibility")

    # ------------------------------------------------------------------
    # Plugin 1: claim-market-router
    # ------------------------------------------------------------------
    def test_claim_market_router_registration_and_auction(self) -> None:
        pkg = load_plugin_package("claim-market-router")
        ctx = MockPluginContext({"auto_effort_shaping": True, "window_budget_tokens": 100000})
        pkg.register(ctx)

        self.assertEqual(set(ctx.tools.keys()), {"claim_market_auction", "claim_market_ledger"})
        self.assertEqual(set(ctx.hooks.keys()), {"post_llm_call", "post_api_request"})
        self.assertEqual(set(ctx.middleware.keys()), {"llm_request"})
        self.assertEqual(len(ctx.delegation_providers), 1)
        for t in ctx.tools.values():
            self._assert_handler_contract(t["handler"])

        # 1. Explorer task -> should select cheap fast route (google/gemini-3.8-flash)
        auction_fn = ctx.tools["claim_market_auction"]["handler"]
        res_explore = json.loads(
            auction_fn({"goal": "Scan repo directory names", "role_needed": "explorer", "complexity": 1})
        )
        self.assertTrue(res_explore["ok"])
        self.assertTrue(res_explore["feasible"])
        self.assertEqual(res_explore["winner"]["name"], "scout-fast")
        self.assertEqual(res_explore["winner"]["model"], "google/gemini-3.8-flash")
        self.assertEqual(res_explore["winner"]["service_tier"], "fast")
        self.assertNotEqual(res_explore["recommended_verifier"], "scout-fast")

        # 2. Finalizer high-complexity task -> should select frontier route (openai/gpt-6-astra-pro)
        res_final = json.loads(
            auction_fn({"goal": "Verify formal safety invariant", "role_needed": "finalizer", "complexity": 5})
        )
        self.assertTrue(res_final["ok"])
        self.assertEqual(res_final["winner"]["name"], "arbiter-frontier")
        self.assertEqual(res_final["winner"]["model"], "openai/gpt-6-astra-pro")

        # 3. Infeasible cost ceiling -> should return explainable sensitivity report
        res_infeasible = json.loads(
            auction_fn(
                {
                    "goal": "Impossible budget task",
                    "role_needed": "implementer",
                    "complexity": 3,
                    "max_cost_units": 0.2,
                }
            )
        )
        self.assertTrue(res_infeasible["ok"])
        self.assertFalse(res_infeasible["feasible"])
        self.assertIn("Sensitivity:", res_infeasible["infeasibility_report"])

        # 4. DelegationProvider route_task contract (including service_tier & fallback_providers) & llm_request middleware
        provider = ctx.delegation_providers[0]
        self.assertEqual(provider.name, "claim_market")
        route = provider.route_task(
            {"goal": "Implement parser module", "role_needed": "implementer", "complexity": 3},
            {},
        )
        self.assertIn("model", route)
        self.assertIn("service_tier", route)
        self.assertIn("fallback_providers", route)
        self.assertIn("label", route)

        # Record high token usage via post_api_request hook and verify llm_request middleware shapes effort
        hook_fn = ctx.hooks["post_api_request"][0]
        hook_fn(
            session_id="s1",
            provider="openrouter",
            model="openai/gpt-6-astra-pro",
            usage={"prompt_tokens": 60000, "completion_tokens": 35000, "total_tokens": 95000},
        )
        mw_fn = ctx.middleware["llm_request"][0]
        # Without reasoning_effort in request, key should not be added
        mw_no_key = mw_fn(request={"model": "openai/gpt-6-astra-pro", "messages": [{"role": "user", "content": "hi"}]})
        self.assertNotIn("reasoning_effort", mw_no_key["request"])

        # When reasoning_effort is already in request, middleware shapes effort
        mw_out = mw_fn(
            request={
                "model": "openai/gpt-6-astra-pro",
                "reasoning_effort": "high",
                "messages": [{"role": "user", "content": "hi"}],
            }
        )
        self.assertEqual(mw_out["request"]["reasoning_effort"], "low")
        self.assertEqual(mw_out["source"], "claim-market-router")

    # ------------------------------------------------------------------
    # Plugin 2: hunk-consent-guard
    # ------------------------------------------------------------------
    def test_hunk_consent_guard_selective_apply_drift_and_rollback(self) -> None:
        pkg = load_plugin_package("hunk-consent-guard")
        ctx = MockPluginContext()
        pkg.register(ctx)

        self.assertEqual(
            set(ctx.tools.keys()),
            {"hunk_propose", "hunk_review_status", "hunk_apply_approved", "hunk_rollback_receipt"},
        )
        self.assertEqual(set(ctx.hooks.keys()), {"pre_tool_call", "post_tool_call"})
        self.assertEqual(set(ctx.middleware.keys()), {"tool_execution"})
        for t in ctx.tools.values():
            self._assert_handler_contract(t["handler"])

        # Verify pre_tool_call escalates hunk_apply_approved to Hermes human approval prompt
        pre_hook = ctx.hooks["pre_tool_call"][0]
        gate = pre_hook(tool_name="hunk_apply_approved", args={"proposal_id": 1})
        self.assertEqual(gate["action"], "approve")

        propose_fn = ctx.tools["hunk_propose"]["handler"]
        review_fn = ctx.tools["hunk_review_status"]["handler"]
        apply_fn = ctx.tools["hunk_apply_approved"]["handler"]
        rollback_fn = ctx.tools["hunk_rollback_receipt"]["handler"]
        slash_fn = ctx.commands["hunk-desk"]["handler"]

        # 0. Protected file (.env) must be refused before reading or storing
        blocked_prop = json.loads(
            propose_fn(
                {
                    "target_path": str(self.temp_dir / ".env"),
                    "proposed_text": "SECRET=1\n",
                }
            )
        )
        self.assertFalse(blocked_prop["ok"])

        target = self.temp_dir / "welcome.md"
        original_content = "Line 1: Hello\nLine 2: Keep me\nLine 3: Keep me too\nLine 4: Goodbye\n"
        target.write_text(original_content, encoding="utf-8")

        proposed_content = "Line 1: Hello World!\nLine 2: Keep me\nLine 3: Keep me too\nLine 4: Farewell!\n"

        # 1. Stage 2-hunk proposal
        prop = json.loads(
            propose_fn(
                {
                    "target_path": str(target),
                    "proposed_text": proposed_content,
                    "summary": "Update greeting and sign-off",
                }
            )
        )
        self.assertTrue(prop["ok"])
        self.assertEqual(prop["hunk_count"], 2)
        self.assertEqual(prop["approved_hunks"], [])
        pid = prop["proposal_id"]

        # 2. Model-facing hunk_review_status cannot approve hunks; user slash command approves hunk 1
        model_attempt = json.loads(review_fn({"proposal_id": pid, "approve_hunks": [1]}))
        self.assertEqual(model_attempt["approved_hunks"], [])

        rev = json.loads(slash_fn(f"approve {pid} 1"))
        self.assertTrue(rev["ok"])
        self.assertEqual(rev["approved_hunks"], [1])

        applied = json.loads(apply_fn({"proposal_id": pid}))
        self.assertTrue(applied["ok"])
        self.assertEqual(
            target.read_text(encoding="utf-8"),
            "Line 1: Hello World!\nLine 2: Keep me\nLine 3: Keep me too\nLine 4: Goodbye\n",
        )
        self.assertGreaterEqual(len(ctx.dispatched_tools), 1)
        self.assertEqual(ctx.dispatched_tools[-1][0], "write_file")
        receipt_id = applied["receipt_id"]

        # 3. Roll back using receipt -> restores exact original text via write_file dispatch
        rb = json.loads(rollback_fn({"receipt_id": receipt_id}))
        self.assertTrue(rb["ok"])
        self.assertEqual(target.read_text(encoding="utf-8"), original_content)

        # 4. Stage another proposal, user approves hunks 1,2, then modify file out-of-band -> drift revokes approvals!
        prop2 = json.loads(
            propose_fn(
                {
                    "target_path": str(target),
                    "proposed_text": proposed_content,
                }
            )
        )
        pid2 = prop2["proposal_id"]
        slash_fn(f"approve {pid2} 1,2")
        target.write_text(original_content + "Out-of-band human edit\n", encoding="utf-8")

        drift_apply = json.loads(apply_fn({"proposal_id": pid2}))
        self.assertFalse(drift_apply["ok"])
        self.assertEqual(drift_apply["status"], "drifted_revoked")

    # ------------------------------------------------------------------
    # Plugin 3: source-trail-supervisor
    # ------------------------------------------------------------------
    def test_source_trail_supervisor_spans_contradiction_and_stuck_loop(self) -> None:
        pkg = load_plugin_package("source-trail-supervisor")
        ctx = MockPluginContext({"stuck_threshold": 3})
        pkg.register(ctx)

        self.assertEqual(
            set(ctx.tools.keys()),
            {"source_trail_ingest", "source_trail_verify", "session_supervisor_node"},
        )
        self.assertEqual(set(ctx.hooks.keys()), {"on_session_start", "post_tool_call", "post_llm_call"})
        self.assertIn("epistemic-supervision", ctx.skills)
        for t in ctx.tools.values():
            self._assert_handler_contract(t["handler"])

        ingest_fn = ctx.tools["source_trail_ingest"]["handler"]
        verify_fn = ctx.tools["source_trail_verify"]["handler"]
        node_fn = ctx.tools["session_supervisor_node"]["handler"]

        doc_a = "Refunds are granted within 14 days of purchase."
        doc_b = "All digital purchases are final and non-refundable."

        # 1. Mismatched quote span fails validation deterministically
        bad = json.loads(
            ingest_fn(
                {
                    "packet_id": "pkt-bad",
                    "sources": [{"id": "s1", "title": "Policy A", "text": doc_a}],
                    "anchors": [
                        {
                            "id": "a1",
                            "source_id": "s1",
                            "start": 0,
                            "end": 10,
                            "quote": "Paraphrased refund claim",
                            "topic": "refund_policy",
                            "position": "allow_14d",
                        }
                    ],
                }
            )
        )
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["status"], "validation_failed")

        # 2. Exact spans with conflicting positions on same topic -> Contradiction Gate withholds claims
        good_ingest = json.loads(
            ingest_fn(
                {
                    "packet_id": "pkt-conflict",
                    "sources": [
                        {"id": "s1", "title": "General Terms", "text": doc_a, "effective_date": "2026-10-01"},
                        {"id": "s2", "title": "Digital Addendum", "text": doc_b, "effective_date": "2026-10-01"},
                    ],
                    "anchors": [
                        {
                            "id": "a1",
                            "source_id": "s1",
                            "start": 0,
                            "end": len(doc_a),
                            "quote": doc_a,
                            "topic": "refund_policy",
                            "position": "refundable_14d",
                        },
                        {
                            "id": "a2",
                            "source_id": "s2",
                            "start": 0,
                            "end": len(doc_b),
                            "quote": doc_b,
                            "topic": "refund_policy",
                            "position": "non_refundable",
                        },
                    ],
                }
            )
        )
        self.assertTrue(good_ingest["ok"])

        gate_res = json.loads(verify_fn({"packet_id": "pkt-conflict"}))
        self.assertTrue(gate_res["ok"])
        self.assertEqual(gate_res["gate_status"], "withheld_contradiction")
        self.assertEqual(gate_res["accepted_claims"], [])
        self.assertEqual(len(gate_res["disagreement_review_list"]), 1)

        # 3. Stuck-session loop detection via post_tool_call hook
        post_tool_hook = ctx.hooks["post_tool_call"][0]
        for _ in range(3):
            post_tool_hook(
                session_id="sess-loop",
                tool_name="terminal",
                args={"command": "pytest tests/failing.py"},
                result='{"error": "exit code 1"}',
            )

        ov = json.loads(node_fn({"action": "overview"}, session_id="sess-loop"))
        self.assertTrue(ov["ok"])
        self.assertTrue(ov["is_stuck"])
        self.assertIn("STUCK DETECTED", ov["remedy"])


if __name__ == "__main__":
    unittest.main()
