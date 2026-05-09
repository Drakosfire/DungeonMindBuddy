"""Contract grader for Stage E NPC hub scaffolding reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    body = text[4:end]
    out: dict[str, str] = {}
    for raw in body.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def _grade_ee1(report: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    if report.get("schema") != "stage_e_npc_hub_scaffold_v1":
        violations.append("EE1: schema mismatch")
    ops = report.get("ops")
    if not isinstance(ops, list):
        violations.append("EE1: ops missing or not list")
        ops = []
    statuses = {
        "preview_ok",
        "preview_error",
        "committed",
        "commit_error",
        "skipped_existing",
    }
    for i, row in enumerate(ops):
        if not isinstance(row, dict):
            violations.append(f"EE1: ops[{i}] not object")
            continue
        st = row.get("status")
        if st not in statuses:
            violations.append(f"EE1: ops[{i}] invalid status {st!r}")
    counts = report.get("counts") or {}
    if isinstance(counts, dict):
        total = sum(
            int(counts.get(k) or 0)
            for k in ("preview_ok", "preview_error", "committed", "commit_error", "skipped_existing")
        )
        if total != len(ops):
            violations.append(
                f"EE1: counts total ({total}) != len(ops) ({len(ops)})"
            )
        if int(counts.get("ops_total") or -1) != len(ops):
            violations.append(
                f"EE1: ops_total ({counts.get('ops_total')}) != len(ops) ({len(ops)})"
            )
    else:
        violations.append("EE1: counts missing or not object")
    return ("PASS" if not violations else "FAIL"), violations, {"ops_count": len(ops)}


def _grade_ee2(report: dict[str, Any], *, corpus_root: Path) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    ops = report.get("ops") or []
    commit_mode = bool(report.get("commit"))
    for i, row in enumerate(ops):
        if not isinstance(row, dict):
            continue
        st = str(row.get("status") or "")
        path = str(row.get("path") or "")
        preview = row.get("preview") if isinstance(row.get("preview"), dict) else {}
        commit = row.get("commit") if isinstance(row.get("commit"), dict) else {}
        if st in {"preview_ok", "committed", "commit_error"}:
            if not preview.get("ok"):
                violations.append(f"EE2: ops[{i}] status={st} missing preview ok")
            if preview.get("phase") != "preview":
                violations.append(f"EE2: ops[{i}] preview phase not preview")
        if st == "preview_error" and preview.get("ok") is not False:
            violations.append(f"EE2: ops[{i}] preview_error but preview.ok != false")
        if st == "committed":
            if not commit.get("ok"):
                violations.append(f"EE2: ops[{i}] committed but commit.ok != true")
            if commit.get("phase") != "committed":
                violations.append(f"EE2: ops[{i}] committed but phase != committed")
            if path and not (corpus_root / path).exists():
                violations.append(f"EE2: ops[{i}] committed file missing on disk: {path}")
        if st == "skipped_existing" and path and not (corpus_root / path).exists():
            violations.append(f"EE2: ops[{i}] skipped_existing but file missing on disk: {path}")
        if commit_mode and st == "preview_ok":
            violations.append(f"EE2: commit run left preview-only row at ops[{i}]")
    return ("PASS" if not violations else "FAIL"), violations, {"commit_mode": commit_mode}


def _grade_ee3(report: dict[str, Any], *, corpus_root: Path) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    checked = 0
    for i, row in enumerate(report.get("ops") or []):
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "")
        if status not in {"committed", "skipped_existing"}:
            continue
        rel = str(row.get("path") or "")
        if not rel:
            continue
        p = corpus_root / rel
        if not p.exists():
            continue
        if rel.endswith("/README.md"):
            fm = _frontmatter(p)
            checked += 1
            if "/Longmont Campaign/" in f"/{rel}":
                if fm.get("canon_layer") != "campaign":
                    violations.append(f"EE3: campaign README missing canon_layer=campaign ({rel})")
                if not fm.get("world_hub_path"):
                    violations.append(f"EE3: campaign README missing world_hub_path ({rel})")
                if not fm.get("divergence_mode"):
                    violations.append(f"EE3: campaign README missing divergence_mode ({rel})")
            if "/Elderwyld/" in f"/{rel}" and "/NPCs/" in f"/{rel}":
                if fm.get("canon_layer") != "world":
                    violations.append(f"EE3: world README missing canon_layer=world ({rel})")
        if rel.endswith("/timeline.md"):
            checked += 1
            txt = p.read_text(encoding="utf-8")
            if "| Session | Beat (short) | Recap / prep |" not in txt:
                violations.append(f"EE3: timeline missing expected header ({rel})")
    return ("PASS" if not violations else "FAIL"), violations, {"checked_files": checked}


def grade_stage_e_scaffold(report: dict[str, Any], *, corpus_root: Path) -> dict[str, Any]:
    ee1_v, ee1_viol, ee1_tel = _grade_ee1(report)
    ee2_v, ee2_viol, ee2_tel = _grade_ee2(report, corpus_root=corpus_root)
    ee3_v, ee3_viol, ee3_tel = _grade_ee3(report, corpus_root=corpus_root)
    per_gate_verdict = {"EE1": ee1_v, "EE2": ee2_v, "EE3": ee3_v}
    violations = ee1_viol + ee2_viol + ee3_viol
    violation_counts = {"EE1": len(ee1_viol), "EE2": len(ee2_viol), "EE3": len(ee3_viol)}
    passed_n = sum(1 for v in per_gate_verdict.values() if v == "PASS")
    return {
        "gates_passed": f"{passed_n}/3",
        "per_gate_verdict": per_gate_verdict,
        "violations": violations,
        "violation_counts": violation_counts,
        "telemetry": {"EE1": ee1_tel, "EE2": ee2_tel, "EE3": ee3_tel},
    }


__all__ = ["grade_stage_e_scaffold"]
