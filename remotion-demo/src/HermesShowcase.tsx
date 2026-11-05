import React from 'react';
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface TermLine {
  appearSec: number;
  text: string;
  color: string;
}

interface CardSpec {
  tag: string;
  title: string;
  subtitle: string;
  metricLabel: string;
  metricValue: string;
  statusColor: string;
}

interface SceneSpec {
  id: string;
  startSec: number;
  endSec: number;
  chapter: string;
  headline: string;
  subheadline: string;
  accent: string;
  secondaryAccent: string;
  terminalTitle: string;
  formulaBanner: string;
  voiceover: string;
  lines: TermLine[];
  cards: CardSpec[];
}

const SCENES: SceneSpec[] = [
  {
    id: 'overview',
    startSec: 0,
    endSec: 8,
    chapter: '01 / ARCHITECTURE  •  NOUS RESEARCH HERMES AGENT HACKATHON',
    headline: 'Extending Hermes Agent Far Beyond Prompts & Skills',
    subheadline:
      'Three Runtime Plugins Derived from misakamikotoghr-5205 Open-Source Systems  •  PR #149353',
    accent: '#38bdf8',
    secondaryAccent: '#818cf8',
    terminalTitle: 'hermes plugins validate --all && python -m unittest',
    formulaBanner:
      'SURFACES: DelegationProvider  •  llm_request & tool_execution Middleware  •  Lifecycle Hooks  •  SQLite Receipts',
    voiceover:
      "Prompts and skills can't intercept model routing, enforce cryptographic file-hunk consent, or gate contradictions. Meet our three runtime plugins for Hermes Agent.",
    lines: [
      {appearSec: 0.3, text: '$ python -B scripts/validate_plugins.py', color: '#38bdf8'},
      {
        appearSec: 1.1,
        text: '[OK] claim-market-router     | tools=2, hooks=3 (post_llm/api + on_delegation), middleware=1, provider=1',
        color: '#22c55e',
      },
      {
        appearSec: 2.0,
        text: '[OK] hunk-consent-guard      | tools=4, hooks=1, middleware=1, slash=1, cli=1',
        color: '#22c55e',
      },
      {
        appearSec: 2.9,
        text: '[OK] source-trail-supervisor | tools=3, hooks=3, skills=1, slash=1, cli=1',
        color: '#22c55e',
      },
      {
        appearSec: 4.0,
        text: '$ python -B -m unittest discover -s tests -v',
        color: '#38bdf8',
      },
      {
        appearSec: 4.9,
        text: 'test_claim_market_router_registration_and_auction ... ok',
        color: '#e2e8f0',
      },
      {
        appearSec: 5.5,
        text: 'test_hunk_consent_guard_selective_apply_drift_and_rollback ... ok',
        color: '#e2e8f0',
      },
      {
        appearSec: 6.1,
        text: 'test_source_trail_supervisor_spans_contradiction_and_stuck_loop ... ok (3/3 in 0.09s)',
        color: '#a855f7',
      },
    ],
    cards: [
      {
        tag: 'CATEGORY: MODELS',
        title: '1. claim-market-router',
        subtitle: 'Market-based DelegationProvider + quota shadow-price effort shaper',
        metricLabel: 'Extension Surface',
        metricValue: 'delegation.backend: claim_market',
        statusColor: '#38bdf8',
      },
      {
        tag: 'CATEGORY: TOOLS',
        title: '2. hunk-consent-guard',
        subtitle: 'Per-hunk patch approval, SHA-256 baseline drift revocation & rollback DB',
        metricLabel: 'Extension Surface',
        metricValue: 'tool_execution middleware + SQLite',
        statusColor: '#22c55e',
      },
      {
        tag: 'CATEGORY: GENERAL',
        title: '3. source-trail-supervisor',
        subtitle: 'Exact Unicode [start,end) spans, contradiction gate & loop supervisor',
        metricLabel: 'Extension Surface',
        metricValue: '3 Hooks + 3 Tools + Bundled Skill',
        statusColor: '#f59e0b',
      },
    ],
  },
  {
    id: 'claim-market',
    startSec: 8,
    endSec: 30,
    chapter: '02 / PLUGIN 1: CLAIM-MARKET-ROUTER (MISAKA AGENT + WATT WINDOW)',
    headline: 'Cheap Models Explore. Strong Models Decide. Expensive Models Finalize.',
    subheadline:
      'DelegationProvider (service_tier + fallback_providers) + on_delegation + llm_request Shaper',
    accent: '#a855f7',
    secondaryAccent: '#38bdf8',
    terminalTitle: 'hermes claim-market [auction | status] & llm_request middleware',
    formulaBanner:
      'CLAIM CONFIDENCE:  c_i = 0.60 * capability_fit_i + 0.40 * quota_health_i - shadow_price(u_i)',
    voiceover:
      'Claim Market Router auctions subagent tasks across Gemini 3.8 Flash, Claude Sonnet 5.5, and GPT-6 Astra Pro with service_tier, fallback chains, and shadow-price effort shaping.',
    lines: [
      {
        appearSec: 8.5,
        text: "$ hermes claim-market auction 'Scan workspace test entrypoints' --role explorer --complexity 1",
        color: '#38bdf8',
      },
      {
        appearSec: 10.2,
        text: '  -> Winner: scout-fast (google/gemini-3.8-flash, tier=fast, cost=1.0, mode=direct_agreement)',
        color: '#22c55e',
      },
      {
        appearSec: 11.4,
        text: '  -> Verifier: arbiter-frontier (openai/gpt-6-astra-pro) | Fallbacks: [deepseek-v4.1-flash]',
        color: '#94a3b8',
      },
      {
        appearSec: 13.5,
        text: "$ hermes claim-market auction 'Audit formal safety invariants' --role finalizer --complexity 5",
        color: '#38bdf8',
      },
      {
        appearSec: 15.2,
        text: '  -> Winner: arbiter-frontier (openai/gpt-6-astra-pro, fallbacks=[claude-opus-5.5, gemini-4-argon])',
        color: '#22c55e',
      },
      {
        appearSec: 17.8,
        text: "$ hermes claim-market auction 'Implement consensus engine' --role implementer --max-cost 0.25",
        color: '#38bdf8',
      },
      {
        appearSec: 19.6,
        text: '  [INFEASIBLE] All 3 routes filtered. Sensitivity: raise max_cost_units by +0.75 (to 1.0).',
        color: '#f59e0b',
      },
      {
        appearSec: 23.0,
        text: '[Hook: post_api_request + on_delegation] 95,000 / 100,000 window tokens -> shadow_price = 0.237',
        color: '#c084fc',
      },
      {
        appearSec: 25.2,
        text: "[Middleware: llm_request] Exploratory turn (1 msg) & shadow >= 0.20 -> reasoning_effort='low'",
        color: '#22c55e',
      },
    ],
    cards: [
      {
        tag: 'WINNER: EXPLORER (1.0x • TIER=FAST)',
        title: 'scout-fast (Gemini 3.8 Flash)',
        subtitle: 'Wins complexity=1 exploration; auto-chains fallback_providers: [deepseek-v4.1-flash]',
        metricLabel: 'Capability Fit / Service Tier',
        metricValue: 'Fit 1.00  •  service_tier="fast"',
        statusColor: '#22c55e',
      },
      {
        tag: 'WINNER: FINALIZER (TIER 5 FRONTIER)',
        title: 'arbiter-frontier (GPT-6 Astra Pro)',
        subtitle: 'Wins complexity=5 verification & finalization; fallbacks: [claude-opus-5.5, gemini-4-argon]',
        metricLabel: 'Vote Weight / Mid Tier',
        metricValue: 'Weight 1.8  •  Claude Sonnet 5.5 (1.4)',
        statusColor: '#a855f7',
      },
      {
        tag: 'QUOTA SHADOW PRICE SHAPER',
        title: 'llm_request + on_delegation',
        subtitle: 'Explains infeasible max_cost_units (+0.75u) & shapes reasoning_effort on high shadow price',
        metricLabel: 'Active Shadow Price (95k/100k)',
        metricValue: 'lambda = 0.237 -> effort="low"',
        statusColor: '#f59e0b',
      },
    ],
  },
  {
    id: 'hunk-consent',
    startSec: 30,
    endSec: 52,
    chapter: '03 / PLUGIN 2: HUNK-CONSENT-GUARD (PATCH REVIEW DESK + CART CONSENT)',
    headline: 'Per-Hunk Patch Consent, SHA-256 Drift Revocation & Rollback Receipts',
    subheadline:
      'tool_execution Middleware + /hunk-desk Selective Hunk Application & Atomic Restoration',
    accent: '#22c55e',
    secondaryAccent: '#38bdf8',
    terminalTitle: 'hermes hunk-desk [status | approve | apply | rollback]',
    formulaBanner:
      'SAFETY INVARIANT:  SHA256(disk_file) == baseline_sha256  OR  status := DRIFTED_REVOKED',
    voiceover:
      'Hunk Consent Guard stages multi-hunk edits, lets you approve Hunk 1 while rejecting Hunk 2, revokes approvals automatically if the file drifts on disk, and rolls back any write by receipt ID.',
    lines: [
      {
        appearSec: 30.5,
        text: '$ hermes hunk-desk status 1   # Target: service_config.py (baseline: 8fa16cebe4a9...)',
        color: '#38bdf8',
      },
      {
        appearSec: 32.0,
        text: '  Hunk #1: -TIMEOUT_SEC = 10    +TIMEOUT_SEC = 30    [status: pending]',
        color: '#e2e8f0',
      },
      {
        appearSec: 33.2,
        text: '  Hunk #2: -DEBUG_MODE = False  +DEBUG_MODE = True   [status: pending]',
        color: '#e2e8f0',
      },
      {
        appearSec: 35.2,
        text: '$ hermes hunk-desk approve 1 1 && hermes hunk-desk apply 1',
        color: '#38bdf8',
      },
      {
        appearSec: 36.8,
        text: '  -> Applied ONLY Hunk [1]! Hunk #2 (DEBUG_MODE=True) rejected. Saved Receipt #1.',
        color: '#22c55e',
      },
      {
        appearSec: 38.6,
        text: "  -> Disk lines: ['TIMEOUT_SEC = 30', 'MAX_RETRIES = 3', 'KEEP_ALIVE = True', 'DEBUG_MODE = False']",
        color: '#94a3b8',
      },
      {
        appearSec: 41.2,
        text: '$ hermes hunk-desk rollback 1',
        color: '#38bdf8',
      },
      {
        appearSec: 42.8,
        text: '  -> Verified after_sha256 intact -> Restored exact baseline (matches_original=True)',
        color: '#22c55e',
      },
      {
        appearSec: 45.8,
        text: '$ echo "# Concurrent human edit" >> service_config.py && hermes hunk-desk apply 2',
        color: '#38bdf8',
      },
      {
        appearSec: 47.5,
        text: '  [DRIFTED_REVOKED] Baseline SHA-256 changed on disk! All hunk approvals automatically revoked.',
        color: '#ef4444',
      },
    ],
    cards: [
      {
        tag: 'SELECTIVE HUNK CONSENT',
        title: 'Approve Hunk #1, Reject Hunk #2',
        subtitle: 'Applies TIMEOUT_SEC = 30 while keeping DEBUG_MODE = False untouched',
        metricLabel: 'Applied Hunk Set',
        metricValue: 'approved_hunks: [1] of [1, 2]',
        statusColor: '#22c55e',
      },
      {
        tag: 'CRYPTOGRAPHIC DRIFT GUARD',
        title: 'SHA-256 Baseline Revocation',
        subtitle: 'Out-of-band file modifications invalidate stale approvals before touching disk',
        metricLabel: 'Drift Verdict',
        metricValue: 'status: "drifted_revoked"',
        statusColor: '#ef4444',
      },
      {
        tag: 'ATOMIC ROLLBACK LEDGER',
        title: 'SQLite Rollback Receipts',
        subtitle: 'Captures before/after SHA-256 & unified diffs across write_file, patch, and hunk apply',
        metricLabel: 'Receipt #1 Verification',
        metricValue: 'before == restored (8fa16cebe4a9)',
        statusColor: '#38bdf8',
      },
    ],
  },
  {
    id: 'source-trail',
    startSec: 52,
    endSec: 69,
    chapter: '04 / PLUGIN 3: SOURCE-TRAIL-SUPERVISOR (SOURCE TRAIL + CASEDESK + SUPERVISOR)',
    headline: 'Exact Unicode [start, end) Spans, Contradiction Gate & Loop Supervisor',
    subheadline:
      'Epistemic Verification Tools + post_tool_call Progress Fingerprinting + Bundled Skill',
    accent: '#f59e0b',
    secondaryAccent: '#38bdf8',
    terminalTitle: 'hermes trail-supervise [verify | overview]',
    formulaBanner:
      'EPISTEMIC GATE:  source[start:end] === quote  AND  |positions(topic)| > 1 => WITHHELD_CONTRADICTION',
    voiceover:
      'Source Trail Supervisor rejects paraphrased quote spans, withholds unilateral claims when valid sources disagree on a topic, and fingerprints tool loops to pivot stuck sessions.',
    lines: [
      {
        appearSec: 52.5,
        text: "$ source_trail_ingest(packet_id='pkt-bad', quote='Paraphrased limit', span=[0, 20])",
        color: '#38bdf8',
      },
      {
        appearSec: 54.1,
        text: "  [VALIDATION_FAILED] Anchor 'a1' mismatch at doc1[0:20]: expected 'Standard API tier al'",
        color: '#ef4444',
      },
      {
        appearSec: 56.5,
        text: "$ hermes trail-supervise verify pkt-rate-conflict   # doc1='60_rpm' vs doc2='10_rpm'",
        color: '#38bdf8',
      },
      {
        appearSec: 58.2,
        text: "  [WITHHELD_CONTRADICTION] Topic 'standard_tier_rpm' has conflicting verified positions!",
        color: '#f59e0b',
      },
      {
        appearSec: 59.8,
        text: "  -> accepted_claims: [] | disagreement_review_list: [{'topic': 'standard_tier_rpm'}]",
        color: '#e2e8f0',
      },
      {
        appearSec: 62.2,
        text: "[Hook: post_tool_call] 3x identical failing fingerprint '8c3b20e277fd4de5' (pytest err=1)",
        color: '#ef4444',
      },
      {
        appearSec: 64.0,
        text: '$ hermes trail-supervise overview --session demo-loop',
        color: '#38bdf8',
      },
      {
        appearSec: 65.5,
        text: '  [STUCK DETECTED] Logged Decision Node #1 -> Switch to alternative_branch (local mock server)',
        color: '#22c55e',
      },
    ],
    cards: [
      {
        tag: 'EXACT UNICODE SPAN VERIFIER',
        title: 'Zero-Based [start, end) Check',
        subtitle: 'Rejects paraphrased or off-by-one citations before they enter the evidence packet',
        metricLabel: 'Span Invariant',
        metricValue: 'doc1[0:54] === quote (SHA-256)',
        statusColor: '#38bdf8',
      },
      {
        tag: 'DETERMINISTIC CONTRADICTION GATE',
        title: 'Withholds Conflicting Claims',
        subtitle: 'Blocks unilateral answers when valid sources hold incompatible positions on a topic',
        metricLabel: 'Gate Verdict',
        metricValue: 'withheld_contradiction (2 sources)',
        statusColor: '#f59e0b',
      },
      {
        tag: 'PROGRESS FINGERPRINT SUPERVISOR',
        title: 'Stuck-Loop & Oscillation Guard',
        subtitle: 'Detects N-repeat & ABAB tool loops via post_tool_call and records causal decision nodes',
        metricLabel: 'Loop Recovery',
        metricValue: '3x 8c3b20e277fd4de5 -> Node #1',
        statusColor: '#22c55e',
      },
    ],
  },
  {
    id: 'outro',
    startSec: 69,
    endSec: 75,
    chapter: '05 / READY FOR THE HERMES PLUGIN CATALOG  •  PULL REQUEST #149353',
    headline: 'Pure Python 3.11+ Stdlib  •  Zero External Dependencies  •  Rule 1–18 Compliant',
    subheadline:
      'github.com/misakamikotoghr-5205/hermes-hackathon-plugins   •   @NousResearch',
    accent: '#38bdf8',
    secondaryAccent: '#a855f7',
    terminalTitle: 'Install & Run in Hermes Agent Today',
    formulaBanner:
      'CATALOG PR: github.com/NousResearch/hermes-agent/pull/149353  •  PINNED SHA: 55834024dc0a8f0019b8062847ba95c87b113237',
    voiceover:
      'All three plugins run on pure Python standard library and profile-scoped SQLite storage. Check out Pull Request 149353 on NousResearch/hermes-agent!',
    lines: [
      {
        appearSec: 69.3,
        text: '$ hermes plugins install claim-market-router',
        color: '#22c55e',
      },
      {
        appearSec: 70.0,
        text: '$ hermes plugins install hunk-consent-guard',
        color: '#22c55e',
      },
      {
        appearSec: 70.7,
        text: '$ hermes plugins install source-trail-supervisor',
        color: '#22c55e',
      },
      {
        appearSec: 71.5,
        text: '$ python -B scripts/run_live_demo.py',
        color: '#38bdf8',
      },
      {
        appearSec: 72.3,
        text: 'ALL THREE PLUGINS EXECUTED LIVE AND VERIFIED SUCCESSFULLY!',
        color: '#c084fc',
      },
    ],
    cards: [
      {
        tag: 'PINNED SHA VERIFIED',
        title: 'claim-market-router',
        subtitle: 'plugin-catalog/claim-market-router.yaml',
        metricLabel: 'Category / Hermes Version',
        metricValue: 'models  •  >=0.22.5',
        statusColor: '#a855f7',
      },
      {
        tag: 'PINNED SHA VERIFIED',
        title: 'hunk-consent-guard',
        subtitle: 'plugin-catalog/hunk-consent-guard.yaml',
        metricLabel: 'Category / Hermes Version',
        metricValue: 'tools  •  >=0.21.5',
        statusColor: '#22c55e',
      },
      {
        tag: 'PINNED SHA VERIFIED',
        title: 'source-trail-supervisor',
        subtitle: 'plugin-catalog/source-trail-supervisor.yaml',
        metricLabel: 'Category / Hermes Version',
        metricValue: 'general  •  >=0.21.5',
        statusColor: '#f59e0b',
      },
    ],
  },
];

const formatClock = (sec: number): string => {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};

const SceneView: React.FC<{scene: SceneSpec; globalSec: number}> = ({
  scene,
  globalSec,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const headerSpring = spring({
    frame,
    fps,
    config: {damping: 16, stiffness: 120, mass: 0.8},
  });

  const headerY = interpolate(headerSpring, [0, 1], [32, 0]);
  const headerOpacity = interpolate(headerSpring, [0, 1], [0, 1]);

  const pulse = 0.5 + 0.5 * Math.sin((frame / fps) * Math.PI * 2);

  return (
    <AbsoluteFill
      style={{
        background:
          'radial-gradient(circle at 18% 15%, #111c38 0%, #070b14 55%, #05070e 100%)',
        color: '#f8fafc',
        fontFamily:
          "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        padding: '44px 64px',
        boxSizing: 'border-box',
      }}
    >
      {/* Subtle animated cyber grid background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'linear-gradient(rgba(148, 163, 184, 0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(148, 163, 184, 0.045) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          pointerEvents: 'none',
        }}
      />

      {/* Glowing ambient orb */}
      <div
        style={{
          position: 'absolute',
          width: 640,
          height: 640,
          right: -120,
          top: -140,
          borderRadius: '50%',
          background: scene.accent,
          opacity: 0.08 + 0.03 * pulse,
          filter: 'blur(110px)',
          pointerEvents: 'none',
        }}
      />

      {/* Top Row: Chapter Pill + Clock & PR Badge */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          transform: `translateY(${headerY}px)`,
          opacity: headerOpacity,
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 12,
            padding: '10px 22px',
            borderRadius: 999,
            background: 'rgba(15, 23, 42, 0.85)',
            border: `2px solid ${scene.accent}`,
            boxShadow: `0 0 24px ${scene.accent}33`,
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: scene.accent,
              boxShadow: `0 0 12px ${scene.accent}`,
            }}
          />
          <span
            style={{
              fontSize: 16,
              fontWeight: 800,
              letterSpacing: 1.1,
              color: scene.accent,
            }}
          >
            {scene.chapter}
          </span>
        </div>

        <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
          <div
            style={{
              padding: '10px 18px',
              borderRadius: 10,
              background: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid #334155',
              fontSize: 15,
              fontWeight: 700,
              color: '#cbd5e1',
              fontFamily: "'Consolas', monospace",
            }}
          >
            PR #149353 • @NousResearch
          </div>
          <div
            style={{
              padding: '10px 20px',
              borderRadius: 10,
              background: 'rgba(15, 23, 42, 0.95)',
              border: `1.5px solid ${scene.accent}`,
              fontSize: 18,
              fontWeight: 800,
              color: '#38bdf8',
              fontFamily: "'Consolas', monospace",
            }}
          >
            ⏱ {formatClock(globalSec)} / 01:15
          </div>
        </div>
      </div>

      {/* Main Title & Subtitle */}
      <div
        style={{
          marginTop: 22,
          transform: `translateY(${headerY}px)`,
          opacity: headerOpacity,
        }}
      >
        <div
          style={{
            fontSize: 40,
            fontWeight: 800,
            letterSpacing: -0.6,
            color: '#f8fafc',
            lineHeight: 1.15,
          }}
        >
          {scene.headline}
        </div>
        <div
          style={{
            fontSize: 21,
            fontWeight: 500,
            color: '#94a3b8',
            marginTop: 8,
          }}
        >
          {scene.subheadline}
        </div>
      </div>

      {/* Formula / Invariant Banner */}
      <div
        style={{
          marginTop: 18,
          padding: '12px 22px',
          borderRadius: 12,
          background: 'linear-gradient(90deg, rgba(15,23,42,0.95), rgba(30,41,59,0.75))',
          borderLeft: `5px solid ${scene.accent}`,
          borderTop: '1px solid rgba(148,163,184,0.18)',
          borderRight: '1px solid rgba(148,163,184,0.18)',
          borderBottom: '1px solid rgba(148,163,184,0.18)',
          fontFamily: "'Consolas', 'Courier New', monospace",
          fontSize: 17,
          fontWeight: 700,
          color: '#e2e8f0',
          letterSpacing: 0.3,
        }}
      >
        {scene.formulaBanner}
      </div>

      {/* Center Split: Left Live Terminal (1120px) + Right 3 Spring Cards (630px) */}
      <div
        style={{
          marginTop: 22,
          display: 'flex',
          gap: 28,
          height: 610,
        }}
      >
        {/* Left Terminal Window */}
        <div
          style={{
            flex: 1.75,
            background: 'rgba(8, 12, 21, 0.96)',
            borderRadius: 18,
            border: '1.5px solid #334155',
            boxShadow: '0 24px 60px rgba(0,0,0,0.65)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Terminal Top Bar */}
          <div
            style={{
              height: 48,
              background: '#111a2e',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              padding: '0 20px',
              justifyContent: 'space-between',
            }}
          >
            <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
              <span
                style={{
                  width: 13,
                  height: 13,
                  borderRadius: '50%',
                  background: '#ef4444',
                }}
              />
              <span
                style={{
                  width: 13,
                  height: 13,
                  borderRadius: '50%',
                  background: '#f59e0b',
                }}
              />
              <span
                style={{
                  width: 13,
                  height: 13,
                  borderRadius: '50%',
                  background: '#22c55e',
                }}
              />
              <span
                style={{
                  marginLeft: 14,
                  fontFamily: "'Consolas', monospace",
                  fontSize: 16,
                  fontWeight: 700,
                  color: '#cbd5e1',
                }}
              >
                {scene.terminalTitle}
              </span>
            </div>
            <span
              style={{
                fontFamily: "'Consolas', monospace",
                fontSize: 13,
                color: scene.accent,
                padding: '4px 10px',
                borderRadius: 6,
                background: 'rgba(56, 189, 248, 0.1)',
              }}
            >
              LIVE EXECUTION
            </span>
          </div>

          {/* Terminal Lines */}
          <div
            style={{
              padding: '24px 26px',
              fontFamily: "'Consolas', 'Courier New', monospace",
              fontSize: 18.5,
              lineHeight: 1.52,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            {scene.lines.map((line, idx) => {
              if (globalSec < line.appearSec) return null;
              const elapsed = globalSec - line.appearSec;
              const charsToShow = Math.min(
                line.text.length,
                Math.max(1, Math.floor(elapsed * 95))
              );
              const visibleText = line.text.slice(0, charsToShow);
              const isTyping = charsToShow < line.text.length;

              const lineSpring = spring({
                frame: Math.max(0, Math.floor(elapsed * fps)),
                fps,
                config: {damping: 18, stiffness: 180},
              });

              return (
                <div
                  key={idx}
                  style={{
                    color: line.color,
                    opacity: interpolate(lineSpring, [0, 1], [0.2, 1]),
                    transform: `translateX(${interpolate(
                      lineSpring,
                      [0, 1],
                      [-12, 0]
                    )}px)`,
                    wordBreak: 'break-word',
                  }}
                >
                  {visibleText}
                  {isTyping && (
                    <span
                      style={{
                        display: 'inline-block',
                        width: 10,
                        height: 19,
                        marginLeft: 4,
                        background: scene.accent,
                        verticalAlign: 'middle',
                      }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Architecture Cards with Staggered Spring Entrances */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: 18,
          }}
        >
          {scene.cards.map((card, idx) => {
            const cardSpring = spring({
              frame: Math.max(0, frame - idx * 8),
              fps,
              config: {damping: 15, stiffness: 130},
            });
            const translateX = interpolate(cardSpring, [0, 1], [48, 0]);
            const opacity = interpolate(cardSpring, [0, 1], [0, 1]);

            return (
              <div
                key={idx}
                style={{
                  flex: 1,
                  background:
                    'linear-gradient(145deg, rgba(17, 26, 46, 0.95), rgba(11, 17, 32, 0.95))',
                  borderRadius: 16,
                  border: `2px solid ${card.statusColor}`,
                  boxShadow: `0 12px 32px rgba(0,0,0,0.45), inset 0 0 24px ${card.statusColor}18`,
                  padding: '18px 24px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  transform: `translateX(${translateX}px)`,
                  opacity,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <span
                    style={{
                      padding: '5px 12px',
                      borderRadius: 6,
                      background: `${card.statusColor}25`,
                      color: card.statusColor,
                      fontSize: 13,
                      fontWeight: 800,
                      letterSpacing: 0.8,
                    }}
                  >
                    {card.tag}
                  </span>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: card.statusColor,
                      boxShadow: `0 0 10px ${card.statusColor}`,
                    }}
                  />
                </div>

                <div>
                  <div
                    style={{
                      fontSize: 23,
                      fontWeight: 800,
                      color: '#f8fafc',
                      marginTop: 4,
                    }}
                  >
                    {card.title}
                  </div>
                  <div
                    style={{
                      fontSize: 15.5,
                      color: '#cbd5e1',
                      marginTop: 4,
                      lineHeight: 1.35,
                    }}
                  >
                    {card.subtitle}
                  </div>
                </div>

                <div
                  style={{
                    paddingTop: 10,
                    borderTop: '1px solid rgba(148, 163, 184, 0.16)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontFamily: "'Consolas', monospace",
                    fontSize: 14.5,
                  }}
                >
                  <span style={{color: '#94a3b8'}}>{card.metricLabel}</span>
                  <span style={{color: card.statusColor, fontWeight: 700}}>
                    {card.metricValue}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Subtitle / Voiceover Bar */}
      <div
        style={{
          marginTop: 22,
          padding: '15px 26px',
          borderRadius: 14,
          background: 'rgba(15, 23, 42, 0.94)',
          border: '1.5px solid #334155',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
        }}
      >
        <span
          style={{
            padding: '6px 12px',
            borderRadius: 8,
            background: scene.accent,
            color: '#05070e',
            fontWeight: 800,
            fontSize: 14,
            letterSpacing: 0.6,
            flexShrink: 0,
          }}
        >
          VOICEOVER
        </span>
        <span
          style={{
            fontSize: 19.5,
            fontWeight: 600,
            color: '#f1f5f9',
            lineHeight: 1.35,
          }}
        >
          {scene.voiceover}
        </span>
      </div>

      {/* Bottom Timeline Progress Bar */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 10,
          background: '#1e293b',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${(globalSec / 75.0) * 100}%`,
            background: `linear-gradient(90deg, ${scene.accent}, ${scene.secondaryAccent})`,
            boxShadow: `0 0 16px ${scene.accent}`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const HermesShowcase: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const globalSec = frame / fps;

  return (
    <AbsoluteFill style={{backgroundColor: '#05070e'}}>
      <Audio src={staticFile('soundtrack.wav')} volume={0.85} />
      {SCENES.map((scene) => {
        const fromFrame = Math.round(scene.startSec * fps);
        const durationInFrames = Math.round(
          (scene.endSec - scene.startSec) * fps
        );
        return (
          <Sequence
            key={scene.id}
            from={fromFrame}
            durationInFrames={durationInFrames}
          >
            <SceneView scene={scene} globalSec={globalSec} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
