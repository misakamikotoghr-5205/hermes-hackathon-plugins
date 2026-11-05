"""Tool schemas for source-trail-supervisor."""

from __future__ import annotations

SOURCE_TRAIL_INGEST = {
    "name": "source_trail_ingest",
    "description": (
        "Ingest a source document packet and verify exact zero-based Unicode code-point "
        "citation spans ([start, end)). Every anchor's substring source.text[start:end] "
        "must strictly equal its verbatim quote. Computes a tamper-evident SHA-256 packet hash."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "packet_id": {
                "type": "string",
                "description": "Unique identifier for this source packet (e.g. 'policy-review-01').",
            },
            "sources": {
                "type": "array",
                "description": "List of source documents ({id, title, text, effective_date}).",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "text": {"type": "string"},
                        "effective_date": {"type": "string"},
                    },
                    "required": ["id", "text"],
                },
            },
            "anchors": {
                "type": "array",
                "description": "List of exact-span quote anchors ({id, source_id, start, end, quote, topic, position}).",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "source_id": {"type": "string"},
                        "start": {"type": "integer"},
                        "end": {"type": "integer"},
                        "quote": {"type": "string"},
                        "topic": {"type": "string"},
                        "position": {"type": "string"},
                    },
                    "required": ["id", "source_id", "start", "end", "quote", "topic", "position"],
                },
            },
        },
        "required": ["packet_id", "sources", "anchors"],
    },
}

SOURCE_TRAIL_VERIFY = {
    "name": "source_trail_verify",
    "description": (
        "Run the deterministic Contradiction & Policy-Conflict Gate over an ingested source packet. "
        "If two valid anchors on the same topic have conflicting position labels, all unilateral "
        "claims are withheld and a structured disagreement_review_list is returned."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "packet_id": {
                "type": "string",
                "description": "The ingested packet_id to verify.",
            },
            "selected_anchor_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional subset of anchor IDs selected for the draft report.",
            },
        },
        "required": ["packet_id"],
    },
}

SESSION_SUPERVISOR_NODE = {
    "name": "session_supervisor_node",
    "description": (
        "Log a recoverable causal decision node (hypothesis, evidence_ref, alternative_branch) "
        "or inspect the session's progress-fingerprint stuck-loop supervisor overview."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["overview", "log_node"],
                "description": "'overview' to inspect stuck status and decision nodes; 'log_node' to record a causal checkpoint.",
            },
            "node_title": {
                "type": "string",
                "description": "Short title for the decision checkpoint (when action='log_node').",
            },
            "hypothesis": {
                "type": "string",
                "description": "Current hypothesis being tested.",
            },
            "evidence_ref": {
                "type": "string",
                "description": "File path, test output, or anchor ID supporting or refuting the hypothesis.",
            },
            "alternative_branch": {
                "type": "string",
                "description": "Fallback plan if this branch gets stuck or fails.",
            },
            "outcome": {
                "type": "string",
                "enum": ["open", "verified", "refuted", "abandoned"],
                "description": "Current status of this decision node.",
            },
        },
        "required": ["action"],
    },
}
