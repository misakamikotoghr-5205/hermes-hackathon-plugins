"""Exact-span Unicode citation verifier and deterministic contradiction gate.

Adapted from:
- misakamikotoghr-5205/source-trail-otari (zero-based Unicode code-point span verification & contradiction gate)
- misakamikotoghr-5205/volc-casedesk (effective-date & policy conflict withholding)
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Mapping, Sequence

from .storage import get_db

MAX_SOURCES = 30
MAX_SOURCE_CHARS = 20000
MAX_AGGREGATE_BYTES = 80 * 1024


def sha256_str(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_and_ingest_packet(
    *,
    packet_id: str,
    sources: Sequence[Mapping[str, Any]],
    anchors: Sequence[Mapping[str, Any]],
    strict_quote_match: bool = True,
) -> dict[str, Any]:
    """Validate a document packet and its exact-span anchors, then store in SQLite."""
    pid = str(packet_id or "").strip()
    if not pid:
        return {"ok": False, "error": "packet_id is required."}
    if not sources or len(sources) > MAX_SOURCES:
        return {"ok": False, "error": f"Packet must contain between 1 and {MAX_SOURCES} sources."}

    source_map: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    for src in sources:
        sid = str(src.get("id") or "").strip()
        title = str(src.get("title") or sid)
        text = str(src.get("text") or "")
        effective_date = str(src.get("effective_date") or "")
        if not sid:
            return {"ok": False, "error": "Every source must have a non-empty 'id'."}
        if sid in source_map:
            return {"ok": False, "error": f"Duplicate source id: {sid!r}."}
        if len(text) > MAX_SOURCE_CHARS:
            return {"ok": False, "error": f"Source {sid!r} exceeds {MAX_SOURCE_CHARS} Unicode code points."}
        total_bytes += len(text.encode("utf-8"))
        if total_bytes > MAX_AGGREGATE_BYTES:
            return {"ok": False, "error": f"Packet exceeds {MAX_AGGREGATE_BYTES} aggregate UTF-8 bytes."}
        source_map[sid] = {
            "id": sid,
            "title": title,
            "text": text,
            "effective_date": effective_date,
            "sha256": sha256_str(text),
        }

    verified_anchors: list[dict[str, Any]] = []
    seen_anchor_ids: set[str] = set()
    seen_spans: set[tuple[str, int, int]] = set()
    validation_errors: list[str] = []

    for anc in anchors:
        aid = str(anc.get("id") or "").strip()
        sid = str(anc.get("source_id") or "").strip()
        quote = str(anc.get("quote") or "")
        topic = str(anc.get("topic") or "general").strip()
        position = str(anc.get("position") or "neutral").strip()

        try:
            start = int(anc.get("start"))  # type: ignore[arg-type]
            end = int(anc.get("end"))  # type: ignore[arg-type]
        except Exception:
            validation_errors.append(f"Anchor {aid or '<unnamed>'}: 'start' and 'end' must be integers.")
            continue

        if not aid:
            validation_errors.append("Anchor is missing 'id'.")
            continue
        if aid in seen_anchor_ids:
            validation_errors.append(f"Duplicate anchor id: {aid!r}.")
            continue
        seen_anchor_ids.add(aid)

        if sid not in source_map:
            validation_errors.append(f"Anchor {aid!r} references unknown source_id {sid!r}.")
            continue

        src_text = source_map[sid]["text"]
        if start < 0 or end <= start or end > len(src_text):
            validation_errors.append(
                f"Anchor {aid!r} span [{start}, {end}) is out of bounds for source {sid!r} (len={len(src_text)})."
            )
            continue

        span_key = (sid, start, end)
        if span_key in seen_spans:
            validation_errors.append(f"Duplicate span [{start}, {end}) on source {sid!r} in anchor {aid!r}.")
            continue
        seen_spans.add(span_key)

        actual_slice = src_text[start:end]
        if strict_quote_match:
            matches = actual_slice == quote
        else:
            matches = " ".join(actual_slice.split()) == " ".join(quote.split())

        if not matches:
            validation_errors.append(
                f"Anchor {aid!r} quote mismatch at {sid}[{start}:{end}]: expected {actual_slice!r}, got {quote!r}."
            )
            continue

        verified_anchors.append(
            {
                "id": aid,
                "source_id": sid,
                "start": start,
                "end": end,
                "quote": actual_slice,
                "topic": topic,
                "position": position,
                "effective_date": source_map[sid]["effective_date"],
            }
        )

    if validation_errors:
        return {
            "ok": False,
            "packet_id": pid,
            "status": "validation_failed",
            "errors": validation_errors,
        }

    canonical_payload = json.dumps(
        {"sources": list(source_map.values()), "anchors": verified_anchors},
        sort_keys=True,
        ensure_ascii=False,
    )
    packet_hash = sha256_str(canonical_payload)

    conn = get_db()
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO source_packets
                    (packet_id, ts, packet_sha256, sources_json, anchors_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    time.time(),
                    packet_hash,
                    json.dumps(list(source_map.values()), ensure_ascii=False),
                    json.dumps(verified_anchors, ensure_ascii=False),
                ),
            )
    finally:
        conn.close()

    return {
        "ok": True,
        "packet_id": pid,
        "packet_sha256": packet_hash,
        "source_count": len(source_map),
        "verified_anchor_count": len(verified_anchors),
        "anchors": verified_anchors,
    }


def verify_selection_and_contradiction_gate(
    *,
    packet_id: str,
    selected_anchor_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Run the deterministic contradiction & policy-conflict gate on a stored source packet.

    If any topic has multiple valid anchors with distinct `position` labels (at the newest
    effective_date if dates are present, as in CaseDesk), all accepted claims are withheld
    and a `disagreement_review_list` is returned.
    """
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM source_packets WHERE packet_id = ?", (str(packet_id),)).fetchone()
        if not row:
            return {"ok": False, "error": f"Packet {packet_id!r} not found. Ingest it first with source_trail_ingest."}

        sources = {s["id"]: s for s in json.loads(row["sources_json"])}
        anchors: list[dict[str, Any]] = json.loads(row["anchors_json"])
        anchor_map = {a["id"]: a for a in anchors}

        if selected_anchor_ids is not None:
            seen_sel: set[str] = set()
            selected: list[dict[str, Any]] = []
            for aid in selected_anchor_ids:
                if aid in seen_sel:
                    return {"ok": False, "error": f"Duplicate selected anchor id: {aid!r}."}
                if aid not in anchor_map:
                    return {"ok": False, "error": f"Unknown selected anchor id: {aid!r}."}
                seen_sel.add(aid)
                selected.append(anchor_map[aid])
        else:
            selected = list(anchors)

        # Deterministic annotation & policy-conflict gate across ALL packet anchors per topic
        by_topic: dict[str, list[dict[str, Any]]] = {}
        for a in anchors:
            by_topic.setdefault(a["topic"], []).append(a)

        disagreements: list[dict[str, Any]] = []
        for topic, topic_anchors in sorted(by_topic.items()):
            # Filter to most recent effective_date if dates are supplied (CaseDesk rule)
            dated = [a for a in topic_anchors if a.get("effective_date")]
            if dated:
                max_date = max(a["effective_date"] for a in dated)
                active_anchors = [a for a in topic_anchors if not a.get("effective_date") or a["effective_date"] == max_date]
            else:
                active_anchors = topic_anchors

            positions = sorted({a["position"] for a in active_anchors})
            if len(positions) > 1:
                disagreements.append(
                    {
                        "topic": topic,
                        "conflicting_positions": positions,
                        "anchors": [
                            {
                                "anchor_id": a["id"],
                                "source_id": a["source_id"],
                                "source_title": sources[a["source_id"]]["title"],
                                "span": [a["start"], a["end"]],
                                "position": a["position"],
                                "effective_date": a.get("effective_date", ""),
                                "verbatim_quote": a["quote"],
                            }
                            for a in active_anchors
                        ],
                    }
                )

        if disagreements:
            report = {
                "ok": True,
                "packet_id": str(packet_id),
                "packet_sha256": row["packet_sha256"],
                "gate_status": "withheld_contradiction",
                "accepted_claims": [],
                "withheld_count": len(selected),
                "disagreement_review_list": disagreements,
                "notice": (
                    "Deterministic Contradiction Gate triggered: conflicting position labels exist "
                    "for the same topic. All unilateral claims are withheld; present the "
                    "disagreement_review_list to the user."
                ),
            }
        else:
            accepted = [
                {
                    "anchor_id": a["id"],
                    "source_id": a["source_id"],
                    "source_title": sources[a["source_id"]]["title"],
                    "span": [a["start"], a["end"]],
                    "topic": a["topic"],
                    "position": a["position"],
                    "verbatim_claim": a["quote"],
                }
                for a in selected
            ]
            report = {
                "ok": True,
                "packet_id": str(packet_id),
                "packet_sha256": row["packet_sha256"],
                "gate_status": "verified_clean",
                "accepted_claims": accepted,
                "withheld_count": 0,
                "disagreement_review_list": [],
            }

        report_json = json.dumps(report, sort_keys=True, ensure_ascii=False)
        report_hash = sha256_str(report_json)
        report["report_sha256"] = report_hash

        with conn:
            conn.execute(
                """
                INSERT INTO verification_reports
                    (ts, packet_id, status, report_sha256, report_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (time.time(), str(packet_id), report["gate_status"], report_hash, report_json),
            )

        return report
    finally:
        conn.close()
