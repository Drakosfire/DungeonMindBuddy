from __future__ import annotations

import re
from typing import Any

SCHEMA = "dmb_c1s4_visibility_v1"


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def infer_c1s4_visibility(record: dict[str, Any]) -> dict[str, Any]:
    source_path = _norm(record.get("source_path") or record.get("source_recap_path") or "")
    text = _norm(
        " ".join(
            str(record.get(k) or "")
            for k in ("title", "section_heading", "snippet", "lexical_plain", "source_reference")
        )
    )
    session_number = record.get("session_number")
    derived_sessions: list[int] = []
    try:
        sn = int(session_number)
        if sn > 0:
            derived_sessions.append(sn)
    except (TypeError, ValueError):
        pass

    future_markers = []
    for marker in ("session 4", "session 04", "session 5", "session 05", "sessions 4", "sessions 4-5", "sessions 4–5"):
        if marker in text or marker in source_path:
            future_markers.append(marker)

    post_session_phrases = [
        "the party arrived",
        "the party visited",
        "campaign-canon location",
        "observed play",
        "records sessions 4",
        "records what is established through observed play",
    ]
    phrase_hits = [p for p in post_session_phrases if p in text]

    planner_visible = True
    reason = "visible_for_c1s4_preplanning"
    role = "pre_session_or_prior_context"
    if "/locations/hempholm/readme.md" in source_path and str(record.get("source_kind") or "") == "location_hub":
        planner_visible = False
        reason = "c1s4_hempholm_campaign_hub_post_session_risk"
        role = "post_session_campaign_canon"
    elif any(s >= 4 for s in derived_sessions):
        planner_visible = False
        reason = "derived_from_future_session"
        role = "post_session_campaign_canon"
    elif future_markers or phrase_hits:
        planner_visible = False
        reason = "future_session_marker_or_observed_play_phrase"
        role = "post_session_campaign_canon"

    return {
        "schema": SCHEMA,
        "visible_for_planning_session": 4,
        "derived_from_sessions": sorted(set(derived_sessions)),
        "derived_from_artifact_role": role,
        "planner_visible": planner_visible,
        "visibility_reason": reason,
        "future_marker_hits": sorted(set(future_markers)),
        "phrase_hits": sorted(set(phrase_hits)),
    }


def is_planner_visible_for_c1s4_preplanning(item: dict[str, Any]) -> bool:
    visibility = item.get("visibility") if isinstance(item.get("visibility"), dict) else infer_c1s4_visibility(item)
    return bool(visibility.get("planner_visible"))
