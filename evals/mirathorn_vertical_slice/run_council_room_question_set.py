from __future__ import annotations

import io
import importlib
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DungeonBuddyCLI = importlib.import_module("src.cli").DungeonBuddyCLI
DEFAULT_CAMPAIGN_ID = "longmont-c1"


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

        lower_answer = answer.lower()
        must_hits = [token for token in row["must"] if token.lower() in lower_answer]
        stale_hits = [token for token in row["stale"] if token.lower() in lower_answer]

        if (
            len(must_hits) >= max(1, len(row["must"]) - 1)
            and not stale_hits
            and not has_error
        ):
            verdict = "pass_updated"
        elif stale_hits:
            verdict = "fail_stale"
        elif has_error:
            verdict = "fail_error"
        else:
            verdict = "fail_incomplete"

        results.append(
            {
                "id": row["id"],
                "question": row["question"],
                "verdict": verdict,
                "must_hits": must_hits,
                "stale_hits": stale_hits,
                "answer": answer,
            }
        )

    summary = {
        "overall": {
            "pass_updated": sum(1 for r in results if r["verdict"] == "pass_updated"),
            "fail_stale": sum(1 for r in results if r["verdict"] == "fail_stale"),
            "fail_incomplete": sum(1 for r in results if r["verdict"] == "fail_incomplete"),
            "fail_error": sum(1 for r in results if r["verdict"] == "fail_error"),
        },
        "results": results,
    }

    (outdir / "council_room_question_set.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    lines = ["# Council Room Question Set Results", ""]
    lines.append(f"- pass_updated: {summary['overall']['pass_updated']}")
    lines.append(f"- fail_stale: {summary['overall']['fail_stale']}")
    lines.append(f"- fail_incomplete: {summary['overall']['fail_incomplete']}")
    lines.append(f"- fail_error: {summary['overall']['fail_error']}")
    lines.append("")

    for row in results:
        lines.append(f"## {row['id']} - {row['verdict']}")
        lines.append(f"- question: {row['question']}")
        lines.append(
            "- must_hits: "
            + (", ".join(row["must_hits"]) if row["must_hits"] else "(none)")
        )
        lines.append(
            "- stale_hits: "
            + (", ".join(row["stale_hits"]) if row["stale_hits"] else "(none)")
        )
        lines.append("")
        lines.append("### answer")
        lines.append(row["answer"])
        lines.append("")

    (outdir / "council_room_question_set.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )

    return summary


if __name__ == "__main__":
    print(json.dumps(run()["overall"], indent=2))
