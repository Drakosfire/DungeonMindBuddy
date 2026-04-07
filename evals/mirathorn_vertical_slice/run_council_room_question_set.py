from __future__ import annotations

import io
import importlib
import json
import os
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DungeonBuddyCLI = importlib.import_module("src.cli").DungeonBuddyCLI
format_projection_context = importlib.import_module(
    "src.agent.context_formatter"
).format_projection_context
attach_scope_relevance_metadata = importlib.import_module(
    "src.reducer.canon_projection"
).attach_scope_relevance_metadata
DEFAULT_CAMPAIGN_ID = "longmont-c1"
GOLD_QUESTIONS_PATH = Path(__file__).resolve().parent / "gold" / "gold_questions.json"
# Artifact writes are opt-in so dry runs / CI / unset shell keys cannot clobber trusted
# bench output when dotenv (e.g. .env.development) repopulates OPENAI_API_KEY.
WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV = (
    "DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS"
)
GLOBAL_STALE_PATTERNS = (
    "nothing changed",
    "no changes",
    "no observed or prep",
    "no observed updates",
    "no observed facts",
    "architecturally unchanged",
)
UPDATE_SIGNAL_TOKENS = (
    "observed",
    "disheveled",
    "activated",
    "fireball",
    "killing blow",
    "decapitated",
    "dead",
    "fades",
)

SEMANTIC_EQUIVALENCES: dict[str, list[str]] = {
    "killing blow": ["decapitated", "head removed", "struck down", "killed"],
    "dead": ["decapitated", "head removed", "death", "killed"],
    "oily sheen fades": ["oily sheen", "sheen fades", "corruption.*fades"],
    "oily sheen": ["oily sheen"],
    "arched ceilings": ["arched", "vaulted ceiling"],
    "floating chandelier": ["chandelier"],
    "secret passage": ["secret passage", "hidden passage", "concealed passage"],
    "chandelier": ["chandelier"],
    "before": ["before", "prior to", "pre-fight"],
    "after": ["after", "post-fight"],
    "arcane lockdown": ["magical lockdown", "ward lockdown"],
    "tradeoff": ["drawback", "cost"],
    # Answers often use Unicode apostrophe (’); must_hit token uses ASCII '
    "wizards' college": [
        "wizards\u2019 college",
        "wizards college",
        "headmaster tinkerbright",
    ],
}


def _normalize_text(text: str) -> str:
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


def _load_gold_questions(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in payload:
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "must": item.get("must_hit_tokens", item.get("must", [])),
                "stale": item.get("stale_tokens", item.get("stale", [])),
                "semantic_equivalences": item.get("semantic_equivalences", {}),
                "update_signal_tokens": item.get(
                    "update_signal_tokens", list(UPDATE_SIGNAL_TOKENS)
                ),
                "must_not_cooccur": item.get("must_not_cooccur", {}),
            }
        )
    if not rows:
        raise ValueError(f"No gold questions loaded from {path}")
    return rows


def _token_negated_by_cooccurrence(
    *,
    token: str,
    answer_lower: str,
    must_not_cooccur: dict[str, list[str]] | None,
) -> bool:
    if not must_not_cooccur:
        return False
    normalized_token = _normalize_text(token).lower()
    for key, negations in must_not_cooccur.items():
        if _normalize_text(key).lower() != normalized_token:
            continue
        for phrase in negations:
            if _normalize_text(phrase).lower() in answer_lower:
                return True
    return False


def classify_answer(
    *,
    must_tokens: list[str],
    stale_tokens: list[str],
    answer: str,
    has_error: bool,
    update_signal_tokens: list[str] | None = None,
    must_not_cooccur: dict[str, list[str]] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    lower_answer = _normalize_text(answer).lower()
    must_hits: list[str] = []
    for token in must_tokens:
        if _normalize_text(token).lower() not in lower_answer:
            continue
        if _token_negated_by_cooccurrence(
            token=token,
            answer_lower=lower_answer,
            must_not_cooccur=must_not_cooccur,
        ):
            continue
        must_hits.append(token)
    stale_hits = [
        token for token in stale_tokens if _normalize_text(token).lower() in lower_answer
    ]
    global_stale_hits = [
        pattern
        for pattern in GLOBAL_STALE_PATTERNS
        if _normalize_text(pattern).lower() in lower_answer
    ]
    effective_update_tokens = update_signal_tokens or list(UPDATE_SIGNAL_TOKENS)
    update_signal_hits = [
        token
        for token in effective_update_tokens
        if _normalize_text(token).lower() in lower_answer
    ]

    # Stale should indicate globally stale state, not localized unchanged traits.
    stale_state = bool(global_stale_hits) or (
        bool(stale_hits) and not must_hits and not update_signal_hits
    )
    if has_error:
        verdict = "fail_error"
    elif (
        len(must_hits) >= max(1, len(must_tokens) - 1)
        and not stale_state
    ):
        verdict = "pass_updated"
    elif stale_state:
        verdict = "fail_stale"
    else:
        verdict = "fail_incomplete"

    return verdict, must_hits, stale_hits, global_stale_hits


def _semantic_token_present(
    token: str,
    answer_lower: str,
    question_equivalences: dict[str, list[str]] | None = None,
) -> bool:
    """Check if *token* or any of its semantic equivalents appear in *answer_lower*."""
    normalized_token = _normalize_text(token).lower()
    if normalized_token in answer_lower:
        return True
    for key, values in (question_equivalences or {}).items():
        if _normalize_text(key).lower() != normalized_token:
            continue
        for equiv in values:
            if re.search(_normalize_text(equiv), answer_lower, re.IGNORECASE):
                return True
    for equiv in SEMANTIC_EQUIVALENCES.get(normalized_token, []):
        if re.search(_normalize_text(equiv), answer_lower, re.IGNORECASE):
            return True
    return False


def classify_answer_semantic(
    *,
    must_tokens: list[str],
    stale_tokens: list[str],
    answer: str,
    has_error: bool,
    question_equivalences: dict[str, list[str]] | None = None,
    update_signal_tokens: list[str] | None = None,
    must_not_cooccur: dict[str, list[str]] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    """Semantic scoring pass: uses equivalence groups instead of literal matching."""
    lower_answer = _normalize_text(answer).lower()
    must_hits: list[str] = []
    for token in must_tokens:
        if not _semantic_token_present(token, lower_answer, question_equivalences):
            continue
        if _token_negated_by_cooccurrence(
            token=token,
            answer_lower=lower_answer,
            must_not_cooccur=must_not_cooccur,
        ):
            continue
        must_hits.append(token)
    stale_hits = [
        token for token in stale_tokens if _normalize_text(token).lower() in lower_answer
    ]
    global_stale_hits = [
        pattern
        for pattern in GLOBAL_STALE_PATTERNS
        if _normalize_text(pattern).lower() in lower_answer
    ]
    effective_update_tokens = update_signal_tokens or list(UPDATE_SIGNAL_TOKENS)
    update_signal_hits = [
        token
        for token in effective_update_tokens
        if _normalize_text(token).lower() in lower_answer
    ]

    stale_state = bool(global_stale_hits) or (
        bool(stale_hits) and not must_hits and not update_signal_hits
    )
    if has_error:
        verdict = "fail_error"
    elif (
        len(must_hits) >= max(1, len(must_tokens) - 1)
        and not stale_state
    ):
        verdict = "pass_updated"
    elif stale_state:
        verdict = "fail_stale"
    else:
        verdict = "fail_incomplete"

    return verdict, must_hits, stale_hits, global_stale_hits


def run() -> dict:
    store = Path("evals/mirathorn_vertical_slice/output/phase_d_store")
    outdir = Path("evals/mirathorn_vertical_slice/output")
    outdir.mkdir(parents=True, exist_ok=True)

    questions = _load_gold_questions(GOLD_QUESTIONS_PATH)

    cli = DungeonBuddyCLI(store_dir=store, verbose=False)
    results: list[dict] = []

    for row in questions:
        capture = io.StringIO()
        with redirect_stdout(capture):
            cli.handle_line(
                f'ask "{row["question"]}" --campaign {DEFAULT_CAMPAIGN_ID} --require-campaign'
            )
        answer = capture.getvalue().strip()
        has_error = bool(re.search(r"Error:\s*(.*)", answer, re.IGNORECASE))

        verdict, must_hits, stale_hits, global_stale_hits = classify_answer(
            must_tokens=row["must"],
            stale_tokens=row["stale"],
            answer=answer,
            has_error=has_error,
            update_signal_tokens=row.get("update_signal_tokens"),
            must_not_cooccur=row.get("must_not_cooccur"),
        )

        sem_verdict, sem_must_hits, sem_stale_hits, sem_global_stale = classify_answer_semantic(
            must_tokens=row["must"],
            stale_tokens=row["stale"],
            answer=answer,
            has_error=has_error,
            question_equivalences=row.get("semantic_equivalences"),
            update_signal_tokens=row.get("update_signal_tokens"),
            must_not_cooccur=row.get("must_not_cooccur"),
        )

        results.append(
            {
                "id": row["id"],
                "question": row["question"],
                "strict_verdict": verdict,
                "semantic_verdict": sem_verdict,
                "must_hits": must_hits,
                "semantic_must_hits": sem_must_hits,
                "stale_hits": stale_hits,
                "global_stale_hits": global_stale_hits,
                "answer": answer,
            }
        )

    def _tally(key: str) -> dict[str, int]:
        return {
            "pass_updated": sum(1 for r in results if r[key] == "pass_updated"),
            "fail_stale": sum(1 for r in results if r[key] == "fail_stale"),
            "fail_incomplete": sum(1 for r in results if r[key] == "fail_incomplete"),
            "fail_error": sum(1 for r in results if r[key] == "fail_error"),
        }

    summary = {
        "overall_strict": _tally("strict_verdict"),
        "overall_semantic": _tally("semantic_verdict"),
        "results": results,
    }

    projection = cli.store.project(DEFAULT_CAMPAIGN_ID)
    scope_cases = [
        {
            "id": "scope_precision_elric_excluded",
            "question": "Catch me up on the council room battle",
            "scope_document_ids": ["doc_battle_with_the_wolf_and_aftermath"],
            "must_include_entities": ["ent_the_wolf", "ent_council_room"],
            "must_exclude_entities": ["ent_commander_elric_vane"],
            "scope_confidence": 1.0,
            "hard_exclude_out_of_scope": True,
        },
        {
            "id": "scope_precision_cold_start_safety",
            "question": "I am starting a fresh world and need anchors",
            "scope_document_ids": ["doc_new_world_bootstrap"],
            "must_include_entities": ["ent_the_wolf"],
            "must_exclude_entities": [],
            "scope_confidence": 0.2,
            "hard_exclude_out_of_scope": True,
        },
        {
            "id": "scope_precision_ambiguous_safety",
            "question": "What happened in that room with Elric?",
            "scope_document_ids": ["doc_unknown_room_reference"],
            "must_include_entities": ["ent_commander_elric_vane"],
            "must_exclude_entities": [],
            "scope_confidence": 0.55,
            "hard_exclude_out_of_scope": True,
        },
    ]

    scope_precision_results: list[dict] = []
    for case in scope_cases:
        scoped_projection = attach_scope_relevance_metadata(
            projection=projection,
            evidence_units=cli.store.evidence_units,
            scope_document_ids=case["scope_document_ids"],
            scope_confidence=float(case["scope_confidence"]),
            min_scope_confidence=0.75,
            min_entity_evidence_count=2,
        )
        context = format_projection_context(
            scoped_projection,
            cli.store.list_entities(),
            question=case["question"],
            evidence_units=cli.store.evidence_units,
            scope_document_ids=case["scope_document_ids"],
            scope_confidence=float(case["scope_confidence"]),
            min_scope_confidence=0.75,
            min_entity_evidence_count=2,
            hard_exclude_out_of_scope=bool(case["hard_exclude_out_of_scope"]),
            unknown_exploration_quota=10,
            include_scope_annotations=True,
        )
        lower_context = context.lower()
        include_pass = all(
            entity_id.replace("ent_", "").replace("_", " ") in lower_context
            for entity_id in case["must_include_entities"]
        )
        exclude_pass = all(
            entity_id.replace("ent_", "").replace("_", " ") not in lower_context
            for entity_id in case["must_exclude_entities"]
        )
        pruning_candidates = (
            scoped_projection.get("scope_relevance", {}).get("pruning_candidates", [])
        )
        scope_precision_results.append(
            {
                "id": case["id"],
                "pass": include_pass and exclude_pass,
                "must_include_entities": case["must_include_entities"],
                "must_exclude_entities": case["must_exclude_entities"],
                "pruning_candidates": pruning_candidates,
            }
        )

    summary["scope_precision_gate"] = {
        "pass": all(item["pass"] for item in scope_precision_results),
        "cases": scope_precision_results,
    }

    def _artifact_write_ok() -> tuple[bool, str]:
        opt = (os.environ.get(WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV) or "").strip()
        if opt != "1":
            return (
                False,
                f"{WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV} is not set to 1; refusing "
                "to write council_room_question_set artifacts (explicit opt-in required).",
            )
        if all(not (row.get("answer") or "").strip() for row in results):
            return (
                False,
                "All answers empty; refusing to overwrite council_room_question_set artifacts.",
            )
        return True, ""

    write_ok, write_reason = _artifact_write_ok()
    if not write_ok:
        summary["artifact_write_skipped"] = True
        summary["artifact_write_reason"] = write_reason
        print(f"WARNING: {write_reason}", file=sys.stderr)
    else:
        summary["artifact_write_skipped"] = False
        summary["artifact_write_reason"] = ""

    if write_ok:
        (outdir / "council_room_question_set.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

    s = summary["overall_strict"]
    sem = summary["overall_semantic"]
    lines = ["# Council Room Question Set Results", ""]
    lines.append("## Strict scoring")
    lines.append(f"- pass_updated: {s['pass_updated']}")
    lines.append(f"- fail_stale: {s['fail_stale']}")
    lines.append(f"- fail_incomplete: {s['fail_incomplete']}")
    lines.append(f"- fail_error: {s['fail_error']}")
    lines.append("")
    lines.append("## Semantic scoring")
    lines.append(f"- pass_updated: {sem['pass_updated']}")
    lines.append(f"- fail_stale: {sem['fail_stale']}")
    lines.append(f"- fail_incomplete: {sem['fail_incomplete']}")
    lines.append(f"- fail_error: {sem['fail_error']}")
    lines.append("")

    if not write_ok:
        lines.append("## Artifact write")
        lines.append(f"- skipped: {write_reason}")
        lines.append("")

    for row in results:
        lines.append(f"## {row['id']} — strict: {row['strict_verdict']} | semantic: {row['semantic_verdict']}")
        lines.append(f"- question: {row['question']}")
        lines.append(
            "- strict must_hits: "
            + (", ".join(row["must_hits"]) if row["must_hits"] else "(none)")
        )
        lines.append(
            "- semantic must_hits: "
            + (", ".join(row["semantic_must_hits"]) if row["semantic_must_hits"] else "(none)")
        )
        lines.append(
            "- stale_hits: "
            + (", ".join(row["stale_hits"]) if row["stale_hits"] else "(none)")
        )
        lines.append("")
        lines.append("### answer")
        lines.append(row["answer"])
        lines.append("")

    if write_ok:
        (outdir / "council_room_question_set.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

    return summary


if __name__ == "__main__":
    out = run()
    print("=== STRICT ===")
    print(json.dumps(out["overall_strict"], indent=2))
    print("=== SEMANTIC ===")
    print(json.dumps(out["overall_semantic"], indent=2))
