#!/usr/bin/env python3
"""Build gold-agnostic benchmark query candidates from the C1S3 breadcrumb artifact.

Reads ``manual_labels/Session 3 - The Stone Bridge Flood.breadcrumbed.md`` (or any
compatible breadcrumb path), normalizes to records, and emits
``dmb_breadcrumb_query_candidates_v1`` JSON under ``artifacts/runs/<date>/``.

This module MUST NOT import or read natural-query gold files.

Example::

  uv run python -m evals.sentence_routing_retrieval_falsification.c1s3_query_candidate_build \\
    --output evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-05/c1s3_query_candidates.json
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "dmb_breadcrumb_query_candidates_v1"


_GM_VOICE_QUESTIONS_BY_UNIT_ID: dict[str, str] = {
    "u-L0003-01": "What was the table hook going into this session — artifact rumor and celebration?",
    "u-L0004-01": "What kind of environmental problem did the rain turn into at the table?",
    "u-L0004-02": "Besides staying alive themselves, what pressure did the recap put on the party?",
    "u-L0006-01": "What was the GM's 'big beats' spine for Session 3?",
    "u-L0008-01": "Who did we ride with early on, and what goat did the table fall for?",
    "u-L0010-01": "Who helped with debris from the broken upriver structure?",
    "u-L0010-02": "What naming TBD did the recap call out for the river/upriver town?",
    "u-L0012-01": "Who comped beer and board after the helpful work?",
    "u-L0014-01": "What did Stafl do at the pub that sold the Wizard's Tower Brewery story?",
    "u-L0016-01": "How did the weather escalate before the real crisis?",
    "u-L0018-01": "What kicked the party out the door when Pippa started yelling?",
    "u-L0020-01": "How did Ephanna first try to reach Bubbles on the rock?",
    "u-L0020-02": "What went wrong when Bubbles panicked on that first mage-hand attempt?",
    "u-L0022-01": "What did Caelynn do to give people footing around Bubble's rock?",
    "u-L0024-01": "Who went in the water and who lost the rope on the first dive beat?",
    "u-L0026-01": "Where did Bonogo end up once the river carried him off?",
    "u-L0028-01": "How did Stafl use the town once nets became part of the plan?",
    "u-L0030-01": "When did Ephanna's mage hand finally stick the landing with Bubbles?",
    "u-L0032-01": "What did Karsemine do right after the comma-beat 'Zephyr strike' line in the outline?",
    "u-L0034-01": "How did the party actually get to StoneBridge with Pippa, Bubbles, and the kegs?",
    "u-L0036-01": "Walk me through arriving at StoneBridge, the pub, the storm, and the moment Pippa bolts for Bubbles.",
    "u-L0038-01": "What was the yell that cut through the rain?",
    "u-L0040-01": "When we rush outside, what is Pippa doing and what's wrong with her dialog beat?",
    "u-L0041-01": "What happens on the second mage-hand attempt when Bubbles bites and the rope drops?",
    "u-L0043-01": "How does Karsemine, Stafl, Caelynn, and Ephanna converge once Bonogo and the boats are gone?",
    "u-L0045-01": "How does the session land: rescue, pub, sleep, and what 'what now' hooks does it tee up?",
}


def _infer_category(*, lexical_plain: str, routes: list[str]) -> str:
    t = lexical_plain.lower()
    r = " ".join(routes).lower()
    if "what now" in t or "mirathorn" in t or "festival" in t:
        return "consequence_or_hook_context"
    if "zephyr" in t or "mage hand" in t or "lasso" in t or "ice" in t:
        return "mechanical_prep_context"
    if "flood" in t or "river" in t or "storm" in t or "locations/" in r:
        return "location_context"
    if "pippa" in t or "bubbles" in t or "kirfan" in t or "grishna" in t or "npcs/" in r:
        return "entity_context"
    if "stafl" in t and "song" in t:
        return "event_context"
    if "parties/" in r:
        return "relationship_or_faction_context"
    return "core_recall"


def _route_needles(norm_route: str) -> list[str]:
    """Substrings suitable for expect_route_substrings (no corpus root prefix)."""
    out: list[str] = []
    m = re.search(r"Campaign 1/[^/]+/[^/\s]+", norm_route)
    if m:
        out.append(m.group(0).rstrip("/"))
    return out or [norm_route.strip("/")[-80:]]


def _draft_must_hit_tokens(lexical_plain: str, limit: int = 8) -> list[str]:
    hits: list[str] = []
    for pat in (
        r"\b\d+\s*gp\b",
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",
    ):
        for m in re.finditer(pat, lexical_plain):
            tok = m.group(0).strip()
            if len(tok) >= 3 and tok not in hits:
                hits.append(tok)
    for w in (
        "Pippa",
        "Bubbles",
        "Kirfan",
        "Grishna",
        "StoneBridge",
        "Stone Bridge",
        "Mirathorn",
        "Zephyr",
        "mage hand",
        "Stafl",
        "Ephanna",
        "Caelynn",
        "Bonogo",
        "Baergrom",
        "Karsemine",
    ):
        if w.lower() in lexical_plain.lower() and w not in hits:
            hits.append(w)
    return hits[:limit]


def build_candidates_payload(
    *,
    records: list[Any],
    source_breadcrumb_path: str,
    campaign_id: str,
    session_number: int,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for rec in records:
        uid = str(getattr(rec, "unit_id", "") or "")
        if uid.startswith("meta-"):
            continue
        lexical = str(getattr(rec, "lexical_plain", "") or "")
        routes = [str(a.normalized_route) for a in (getattr(rec, "routes", None) or [])]
        needles: list[str] = []
        for rt in routes:
            needles.extend(_route_needles(rt))
        seen: set[str] = set()
        needles = [n for n in needles if not (n in seen or seen.add(n))]
        cat = _infer_category(lexical_plain=lexical, routes=routes)
        snippet = lexical[:420] + ("…" if len(lexical) > 420 else "")
        q = _GM_VOICE_QUESTIONS_BY_UNIT_ID.get(
            uid,
            "What should I remember from this Session 3 beat for next prep?",
        )
        candidates.append(
            {
                "candidate_id": f"c1s3_cand_{uid.replace('-', '_')}",
                "category": cat,
                "question": q,
                "expected_answer_draft": lexical,
                "must_hit_tokens_draft": _draft_must_hit_tokens(lexical),
                "supporting_unit_ids": [uid],
                "supporting_route_substrings": needles,
                "supporting_evidence_snippets": [snippet],
                "notes": "Draft from deterministic unit walk; human should rewrite question into natural GM phrasing.",
                "review_status": "pending",
            }
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return {
        "schema": SCHEMA,
        "generated_at_utc": stamp,
        "source_breadcrumb_path": source_breadcrumb_path,
        "campaign_id": campaign_id,
        "session_number": session_number,
        "candidates": candidates,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--breadcrumb-md",
        type=Path,
        default=Path(
            "evals/sentence_routing_retrieval_falsification/manual_labels/"
            "Session 3 - The Stone Bridge Flood.breadcrumbed.md"
        ),
    )
    p.add_argument("--corpus-root", type=Path, default=Path("corpus/eldyrwild-markdown"))
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write candidate JSON here (default: artifacts/runs/<today>/c1s3_query_candidates_<stamp>.json)",
    )
    args = p.parse_args()

    from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (  # noqa: WPS433
        extract_meta_from_frontmatter,
        normalize_breadcrumb_artifact,
        parse_frontmatter_and_body,
    )

    text = args.breadcrumb_md.read_text(encoding="utf-8")
    fm, _body = parse_frontmatter_and_body(text)
    if fm is None:
        raise SystemExit("missing frontmatter")
    meta = extract_meta_from_frontmatter(fm)
    records, _norm_meta = normalize_breadcrumb_artifact(
        artifact_text=text,
        corpus_root=args.corpus_root,
    )
    campaign_id = str(meta.get("campaign_id") or "longmont-c1")
    session_number = int(meta.get("session_number") or 3)
    rel_path = str(args.breadcrumb_md)
    payload = build_candidates_payload(
        records=records,
        source_breadcrumb_path=rel_path,
        campaign_id=campaign_id,
        session_number=session_number,
    )
    out = args.output
    if out is None:
        suite = Path(__file__).resolve().parent
        stamp = payload["generated_at_utc"]
        out = suite / "artifacts" / "runs" / str(date.today()) / f"c1s3_query_candidates_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out), "candidate_count": len(payload["candidates"])}, indent=2))


if __name__ == "__main__":
    main()
