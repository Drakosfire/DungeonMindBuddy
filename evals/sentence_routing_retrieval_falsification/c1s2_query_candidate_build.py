#!/usr/bin/env python3
"""Build gold-agnostic benchmark query candidates from the C1S2 breadcrumb artifact.

Reads ``manual_labels/Session 2 - Finishing the Job.breadcrumbed.md`` (or any
compatible breadcrumb path), normalizes to records, and emits
``dmb_breadcrumb_query_candidates_v1`` JSON under ``artifacts/runs/<date>/``.

This module MUST NOT import or read natural-query gold files.

Example::

  uv run python -m evals.sentence_routing_retrieval_falsification.c1s2_query_candidate_build \\
    --output evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-05/c1s2_query_candidates.json
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "dmb_breadcrumb_query_candidates_v1"


_GM_VOICE_QUESTIONS_BY_UNIT_ID = {
    "u-L0003-01": "Remind me how the crew came out of the tower-basement mess overall.",
    "u-L0003-02": "What were the weird basement threats again, and how scary did they feel compared to the rats?",
    "u-L0005-01": "After they finished clearing the wizard tower basement, what was the broad outcome for the party?",
    "u-L0005-02": "What loot and strange alchemy-room stuff did they actually uncover down there?",
    "u-L0005-03": "Did the party know what to do with those ancient alchemy tools yet, or was it just cool treasure for now?",
    "u-L0007-01": "What deal did they work out with Glowkindle once the original rat job had gone wildly off-script?",
    "u-L0007-02": "What was the vibe on that hidden-room arrangement: a real foothold, or just the first tiny step?",
    "u-L0009-01": "Where did the party land after the job: pay, lessons learned, and are they sticking together?",
    "u-L0011-01": "What obvious next-job hook is sitting there with Glowkindle?",
    "u-L0011-02": "If they head back toward Stonebridge, who and where might they naturally check in with?",
    "u-L0011-03": "What Wizard's Tower question does the recap tee up, without answering it yet?",
    "u-L0013-01": "How does the recap leave the table hanging at the end?",
}


def _infer_category(*, lexical_plain: str, routes: list[str]) -> str:
    t = lexical_plain.lower()
    r = " ".join(routes).lower()
    if any(x in t for x in ("giant flaming spider", "giant centipede", "mutate", "compared to the rats")):
        return "mechanical_prep_context"
    if "will they" in t or "stay tuned" in t:
        return "consequence_or_hook_context"
    if "25 gp" in t or "stick together" in t:
        return "relationship_or_faction_context"
    if "glowkindle" in t or "negotiated" in t or "stash" in t or "contract" in t:
        return "event_context"
    if "gems" in t or "potions" in t or "alchem" in t or "basement" in t:
        return "event_context"
    if "location" in r or "locations/" in r:
        return "location_context"
    if "npcs/" in r:
        return "entity_context"
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
    # Proper-noun-ish tokens and key numerics from the beat
    hits: list[str] = []
    for pat in (
        r"\b\d+\s*gp\b",
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",
    ):
        for m in re.finditer(pat, lexical_plain):
            tok = m.group(0).strip()
            if len(tok) >= 3 and tok not in hits:
                hits.append(tok)
    for w in ("Glowkindle", "Grishna", "Stonebridge", "rats", "spider", "centipede", "gems", "potions"):
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
        # de-dupe preserve order
        seen: set[str] = set()
        needles = [n for n in needles if not (n in seen or seen.add(n))]
        cat = _infer_category(lexical_plain=lexical, routes=routes)
        snippet = lexical[:420] + ("…" if len(lexical) > 420 else "")
        q = _GM_VOICE_QUESTIONS_BY_UNIT_ID.get(
            uid,
            "What should I remember from this Session 2 beat?",
        )
        candidates.append(
            {
                "candidate_id": f"c1s2_cand_{uid.replace('-', '_')}",
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
            "Session 2 - Finishing the Job.breadcrumbed.md"
        ),
    )
    p.add_argument("--corpus-root", type=Path, default=Path("corpus/eldyrwild-markdown"))
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write candidate JSON here (default: artifacts/runs/<today>/c1s2_query_candidates_<stamp>.json)",
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
    session_number = int(meta.get("session_number") or 2)
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
        out = suite / "artifacts" / "runs" / str(date.today()) / f"c1s2_query_candidates_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out), "candidate_count": len(payload["candidates"])}, indent=2))


if __name__ == "__main__":
    main()
