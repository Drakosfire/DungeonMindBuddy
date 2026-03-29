from __future__ import annotations

import io
import importlib
import json
import os
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DungeonBuddyCLI = importlib.import_module("src.cli").DungeonBuddyCLI
DEFAULT_CAMPAIGN_ID = "longmont-c1"
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
}


def classify_answer(
    *,
    must_tokens: list[str],
    stale_tokens: list[str],
    answer: str,
    has_error: bool,
) -> tuple[str, list[str], list[str], list[str]]:
    lower_answer = answer.lower()
    must_hits = [token for token in must_tokens if token.lower() in lower_answer]
    stale_hits = [token for token in stale_tokens if token.lower() in lower_answer]
    global_stale_hits = [p for p in GLOBAL_STALE_PATTERNS if p in lower_answer]
    update_signal_hits = [t for t in UPDATE_SIGNAL_TOKENS if t in lower_answer]

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


def _semantic_token_present(token: str, answer_lower: str) -> bool:
    """Check if *token* or any of its semantic equivalents appear in *answer_lower*."""
    if token.lower() in answer_lower:
        return True
    for equiv in SEMANTIC_EQUIVALENCES.get(token.lower(), []):
        if re.search(equiv, answer_lower, re.IGNORECASE):
            return True
    return False


def classify_answer_semantic(
    *,
    must_tokens: list[str],
    stale_tokens: list[str],
    answer: str,
    has_error: bool,
) -> tuple[str, list[str], list[str], list[str]]:
    """Semantic scoring pass: uses equivalence groups instead of literal matching."""
    lower_answer = answer.lower()
    must_hits = [t for t in must_tokens if _semantic_token_present(t, lower_answer)]
    stale_hits = [t for t in stale_tokens if t.lower() in lower_answer]
    global_stale_hits = [p for p in GLOBAL_STALE_PATTERNS if p in lower_answer]
    update_signal_hits = [t for t in UPDATE_SIGNAL_TOKENS if t in lower_answer]

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

    questions = [
        {
            "id": "q_arch_current",
            "question": "What is the Council Room architecture like right now after the wolf fight?",
            "must": ["arched ceilings", "floating chandelier", "secret passage"],
            "stale": ["undamaged", "unchanged"],
        },
        {
            "id": "q_arch_delta",
            "question": "What physical changes to the Council Room happened during Session 12?",
            "must": ["chandelier", "runes", "secret passage"],
            "stale": ["no damage", "nothing changed"],
        },
        {
            "id": "q_wolf_status",
            "question": "What is the Wolf's status at the end of Session 12, including corruption state?",
            "must": ["killing blow", "dead", "oily sheen fades"],
            "stale": ["alive", "uncorrupted throughout"],
        },
        {
            "id": "q_pre_post",
            "question": "Contrast the Wolf before the council fight versus after it ends.",
            "must": ["before", "after", "oily sheen", "killing blow"],
            "stale": ["same state"],
        },
        {
            "id": "q_thalia",
            "question": "Was Thalia corrupted or manipulated, and how does that relate to Wolf evidence?",
            "must": ["ensorcelled", "wolf", "not corrupted"],
            "stale": ["thalia was corrupted"],
        },
    ]

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
        )

        sem_verdict, sem_must_hits, sem_stale_hits, sem_global_stale = classify_answer_semantic(
            must_tokens=row["must"],
            stale_tokens=row["stale"],
            answer=answer,
            has_error=has_error,
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
