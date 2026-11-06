"""Tool schemas for hunk-consent-guard."""

from __future__ import annotations

HUNK_PROPOSE = {
    "name": "hunk_propose",
    "description": (
        "Stage a multi-hunk file edit proposal without modifying the file on disk. "
        "Computes the file's SHA-256 baseline hash and splits changes into numbered hunks "
        "for selective approval. If the file changes on disk before apply, approvals are "
        "automatically revoked."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target_path": {
                "type": "string",
                "description": "Path to the file to stage edits for.",
            },
            "proposed_text": {
                "type": "string",
                "description": "Complete proposed file contents to diff against the current baseline.",
            },
            "summary": {
                "type": "string",
                "description": "Short rationale for the proposed changes.",
            },
        },
        "required": ["target_path", "proposed_text"],
    },
}

HUNK_REVIEW_STATUS = {
    "name": "hunk_review_status",
    "description": (
        "Read-only inspection of a staged hunk proposal and its SHA-256 baseline status on disk "
        "(automatically revoking approvals if the file drifted). Hunk approval is user-only via "
        "`/hunk-desk approve <id> <h1,h2>` or `hermes hunk-desk approve <id> <h1,h2>`."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "proposal_id": {
                "type": "integer",
                "description": "Proposal ID to inspect. Omit to list recent proposals and receipts.",
            },
        },
    },
}

HUNK_APPLY_APPROVED = {
    "name": "hunk_apply_approved",
    "description": (
        "Apply only the approved hunks of a staged proposal to the target file after verifying "
        "that the file's SHA-256 baseline has not drifted. Emits a durable rollback receipt."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "proposal_id": {
                "type": "integer",
                "description": "The staged proposal ID whose approved hunks should be applied.",
            },
        },
        "required": ["proposal_id"],
    },
}

HUNK_ROLLBACK_RECEIPT = {
    "name": "hunk_rollback_receipt",
    "description": (
        "Roll back a previously applied file modification using its receipt ID. "
        "Verifies that the current file SHA-256 matches the receipt's post-apply hash "
        "so later edits are never overwritten."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "receipt_id": {
                "type": "integer",
                "description": "Receipt ID to roll back.",
            },
        },
        "required": ["receipt_id"],
    },
}
