"""Gated live extractor prompt harness helpers (manual LLM dogfood only)."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from evals.graph_memory_layer.reconcile_live_candidate import (
    ENVELOPE_SCHEMA,
    FORBIDDEN_OUTPUT_TOKENS,
    validate_live_candidate_output,
)
from src.graph_memory.candidate_graph_preview import (
    CANON_STATES,
    LIFECYCLE_STATES,
    NODE_TYPES,
    WRITE_TYPES,
)

SCHEMA = "dmb_live_extractor_prompt_manifest_v0"
VERSION = "0.1"
FIXTURE_ID = "graph-memory:live-extractor-prompt-harness:v0"
PACKET_SCHEMA = "dmb_live_extractor_prompt_packet_manifest_v0"
SUMMARY_SCHEMA = "dmb_live_extractor_source_packet_summary_v0"
EXAMPLE_DIR = "evals/graph_memory_layer/examples/live_extractor_prompt_harness"
MANIFEST_PATH = f"{EXAMPLE_DIR}/live_extractor_prompt_manifest.json"
SAMPLE_PACKET_PATH = f"{EXAMPLE_DIR}/session_23_prompt_packet_manifest.json"
RUNS_DIR = "evals/graph_memory_layer/runs/live_extractor_prompt_harness"
SESSION_23_RUN_BUNDLE = "evals/graph_memory_layer/examples/live_recap_ingest_run_bundle/session_23_sample"
SESSION_23_SOURCE_RECAP = "evals/graph_memory_layer/examples/session_23_recap_ingest/expected_normalized_recap.md"
MODES = ("one_shot", "two_shot", "three_shot")
PROMPT_FILES = {
    "one_shot": ["one_shot_prompt.md"],
    "two_shot": ["observation_extraction_prompt.md", "graph_assembly_prompt.md"],
    "three_shot": ["observation_prompt.md", "relation_prompt.md", "assembly_prompt.md"],
}
ENVELOPE_SECTIONS = ("candidate_graph", "review_sidecar")
GRAPH_SECTIONS = ("nodes", "edges", "beats", "proposed_writes", "ignored_items", "deferred_items", "diagnostics")


class HarnessValidationError(ValueError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _abs(p: Path) -> Path:
    return p if p.is_absolute() else repo_root() / p


def _load_json(p: Path) -> dict[str, Any]:
    return json.loads(_abs(p).read_text(encoding="utf-8"))


def _sha_text(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _is_glob(s: str) -> bool:
    return any(c in s for c in "*?[]{}")


def _assert(c: bool, msg: str) -> None:
    if not c:
        raise HarnessValidationError(msg)


def validate_source_recap_path(path: Path) -> Path:
    _assert(not _is_glob(str(path)), "source_recap_is_glob")
    p = _abs(path)
    _assert(p.exists(), "source_recap_missing")
    _assert(p.is_file(), "source_recap_is_directory")
    return p


def validate_output_path(out_dir: Path, *, allow_overwrite: bool = False) -> Path:
    _assert(not _is_glob(str(out_dir)), "output_is_glob")
    root = repo_root()
    target = _abs(out_dir).resolve()
    allowed = (root / RUNS_DIR).resolve()
    _assert(target != allowed and allowed in target.parents, "output_outside_allowed_run_dir")
    if allow_overwrite:
        _assert(target != allowed, "cannot_overwrite_run_root")
    return target


def load_run_bundle(run_bundle: Path) -> dict[str, Any]:
    base = _abs(run_bundle)
    _assert(base.exists() and base.is_dir(), "run_bundle_missing")
    names = ("run_manifest", "source_artifact", "source_units", "source_span_index", "provenance_index", "diagnostics")
    return {n: json.loads((base / f"{n}.json").read_text(encoding="utf-8")) for n in names}


def verify_run_bundle_and_source(run_bundle: Path, source_recap: Path) -> dict[str, Any]:
    b = load_run_bundle(run_bundle)
    p = validate_source_recap_path(source_recap)
    text = p.read_text(encoding="utf-8")
    m = b["run_manifest"]
    d = b["diagnostics"]
    boundary = d.get("boundary", {})
    _assert(_sha_text(text) == m["source"]["input_sha256"], "source_recap_sha256_mismatch")
    _assert(len(text.splitlines()) == m["source"]["input_line_count"], "source_recap_line_count_mismatch")
    _assert(d.get("status") == "ready", "run_bundle_diagnostics_not_ready")
    for k in ("graph_write_allowed", "query_execution_allowed", "plan_connected", "agent_interaction_connected", "corpus_scan_allowed", "corpus_mutation_allowed"):
        _assert(boundary.get(k) is False, f"unsafe_run_bundle_boundary:{k}")
    units = b["source_units"]["units"]
    spans = b["source_span_index"]["spans"]
    span_by_unit = {s["source_unit_id"]: s for s in spans}
    _assert(len(span_by_unit) == len(spans), "duplicate_source_span_refs")
    for u in units:
        sp = span_by_unit.get(u["source_unit_id"])
        _assert(bool(sp and sp.get("source_span_ref_id")), "source_unit_missing_span_ref")
    return {"bundle": b, "source_text": text, "source_path": p, "span_by_unit": span_by_unit}


def source_packet_rows(verified: Mapping[str, Any]) -> list[dict[str, Any]]:
    lines = verified["source_text"].splitlines()
    rows = []
    for u in verified["bundle"]["source_units"]["units"]:
        sp = verified["span_by_unit"][u["source_unit_id"]]
        text = "\n".join(lines[u["line_start"] - 1 : u["line_end"]])
        rows.append(
            {
                "source_span_ref_id": sp["source_span_ref_id"],
                "source_unit_id": u["source_unit_id"],
                "line_start": u["line_start"],
                "line_end": u["line_end"],
                "text": text,
            }
        )
    return rows


def _source_packet_md(rows: list[dict[str, Any]]) -> str:
    parts = []
    for r in rows:
        parts.append(
            f"### {r['source_span_ref_id']} / {r['source_unit_id']} / lines {r['line_start']}-{r['line_end']}\n\n```text\n{r['text']}\n```"
        )
    return "\n\n".join(parts)


def _ir_schema_scaffold() -> str:
    node_types = ", ".join(sorted(NODE_TYPES))
    write_types = ", ".join(sorted(WRITE_TYPES))
    return f"""## Output envelope (strict JSON only)

Return one JSON object:
- `schema`: `{ENVELOPE_SCHEMA}`
- `version`: `0.1`
- `candidate_graph`: canonical Candidate Graph Preview IR (`dmb_candidate_graph_preview_v0`)
- `review_sidecar`: `high_risk_claims` (array) and optional `notes` (array)

### candidate_graph required top-level keys

`schema`, `version`, `preview_id`, `campaign_id`, `session_id`, `source_artifact_ids`, `status` (must be `preview`), `nodes`, `edges`, `beats`, `proposed_writes`, `ignored_items`, `deferred_items`, `diagnostics`.

### Evidence contract (model-facing)

Every positive factual object MUST include `evidence_refs` as an array of objects with ONLY:
`{{"source_span_ref_id": "<spref from source packet>"}}`
Do not invent anchor ids, line numbers, or resolver fields.

### Node fields

`node_id`, `label`, `node_type` (one of: {node_types}), `description`, `importance` (`high`|`medium`|`low`), `semantic_state` object with `canon_state` ({", ".join(sorted(CANON_STATES))}), `lifecycle_state` (use `candidate`), `evidence_role` (`source_evidence`), `authority_state` (`system_derived`), `visibility_state` (`gm_private`), `evidence_refs`, `proposed_action` (`create`), `confidence` (`high`|`medium`|`low`), optional `warnings`.

Unnamed-but-important concepts are `nodes` with `node_type: unknown_important` (not a separate section).

### Edge fields

`edge_id`, `from_node_id`, `to_node_id`, `label`, `relationship_type`, `semantic_state`, `evidence_refs`, `proposed_action`, `confidence`, optional `warnings`.
Relationship types to consider: origin, role, familial, location, allegiance, combat_trait, attribute, association.

### Beat fields

`beat_id`, `order` (positive int), `title`, `summary`, `involved_node_ids`, `evidence_refs`, optional `unresolved_thread_node_ids`, `proposed_action`, optional `warnings`.
Extract one beat per major scene transition; do not merge beats without recording merge rationale in `diagnostics`.

### Proposed write fields

`write_id`, `write_type` (one of: {write_types}), `target_id`, `label`, `reason`, `evidence_refs`, `status` (must be `pending`).

### Ignored / deferred item fields

`item_id`, `label`, `reason`, `evidence_refs`, optional `warnings`; deferred may include `suggested_next_step`.

### diagnostics (required)

`preview_only: true`, `extraction_performed: false`, `llm_used: false`, `runtime_connected: false`, `plan_connected: false`, `agent_interaction_connected: false`, `corpus_scanned: false`, `corpus_mutated: false`, `facts_promoted: false`, `canon_promoted: false`, `unresolved_evidence_refs: 0`, `missing_evidence_objects: 0`, `warning_count: <int>`."""


def _uncertainty_rules() -> str:
    return """## Uncertainty preservation (mandatory)

- Do not resolve cliffhangers or battle outcomes.
- Do not bind aliases across spans unless a single cited span explicitly links them.
- Named-in-span-A / described-in-span-B: if an entity is named in one span and only described in another (e.g. "her father" vs a name elsewhere), keep separate nodes or defer identity — do not merge without multi-span evidence on the binding claim.
- Do not state exact counts when the source gives a range (e.g. "twenty to one hundred" shadows).
- Do not promote canon, approve memory, or execute writes."""


def _high_risk_sidecar_rules() -> str:
    return """## review_sidecar.high_risk_claims

Each entry MUST include:
- `claim_id`
- `risk_type` (alias_binding | identity_binding | inferred_relationship | cliffhanger_outcome | uncertain_count | unsupported_canon | weak_evidence)
- `unsafe_interpretation` (what would be dangerous to treat as fact)
- `safe_interpretation` (what the cited spans actually support)
- `evidence_refs` with `source_span_ref_id`

Use audit-negative wording in unsafe/safe fields — never assert the risky claim as true."""


def _safety_boundary() -> str:
    return """## Safety boundary

Forbidden: approve memory, commit graph records, promote canon/facts, execute writes, produce query results, emit runtime or /plan or Agent Interaction payloads, mutate corpus.
Proposed writes are pending preview intent only — never approved or persisted."""


def _exhaustiveness_rules() -> str:
    return """## Exhaustiveness

- Extract all directly named characters, locations, factions, and groups.
- Propose relationship edges for every source-supported link (origin, role, familial, location, allegiance, combat traits).
- Include ignored items (table/mechanical noise) and deferred items (unresolved threads, ambiguous identity, battle outcome).
- Target completeness over minimalism; cite evidence for every positive claim."""


def safety_instructions() -> str:
    return (
        "You are producing preview-only graph-memory candidates for manual benchmark review.\n"
        "Return ONLY valid JSON matching the envelope contract below.\n"
        + _safety_boundary()
    )


def render_prompts(mode: str, verified: Mapping[str, Any]) -> dict[str, str]:
    _assert(mode in MODES, "unknown_mode")
    rows = source_packet_rows(verified)
    src = _source_packet_md(rows)
    scaffold = _ir_schema_scaffold()
    uncertainty = _uncertainty_rules()
    high_risk = _high_risk_sidecar_rules()
    exhaust = _exhaustiveness_rules()
    common = f"{safety_instructions()}\n\n{scaffold}\n\n{uncertainty}\n\n{high_risk}\n\n{exhaust}\n\n## Source Packet\n\n{src}\n"

    if mode == "one_shot":
        return {"one_shot_prompt.md": f"# Live Graph Memory Extractor — One Shot\n\n{common}"}

    if mode == "two_shot":
        obs = f"# Live Graph Memory Extractor — Observation Extraction\n\n{safety_instructions()}\n\n{uncertainty}\n\nExtract observations only as JSON with sections: `observation_beats`, `observation_nodes`, `observation_edges`, `ignored_items`, `deferred_items`. Every observation cites `source_span_ref_id`. Do not assemble final candidate_graph yet.\n\n## Source Packet\n\n{src}\n"
        assembly = f"# Live Graph Memory Extractor — Graph Assembly\n\n{_safety_boundary()}\n\nUsing the manually supplied observation JSON, assemble the full output envelope (`candidate_graph` + `review_sidecar`).\n\nAssembly rules:\n- Do not add facts absent from observations and their cited spans.\n- Preserve every observation beat and edge unless merged; record any merge in `candidate_graph.diagnostics.warning_count` and `review_sidecar.notes`.\n- Never drop beats or edges silently.\n\n{scaffold}\n\n{high_risk}\n"
        return {"observation_extraction_prompt.md": obs, "graph_assembly_prompt.md": assembly}

    obs = f"# Live Graph Memory Extractor — Observation Pass\n\n{safety_instructions()}\n\n{uncertainty}\n\nPass 1: beats, named entities, unnamed-important concepts (as nodes), ignored/deferred items. JSON sections: `observation_beats`, `observation_nodes`, `ignored_items`, `deferred_items`. Every item cites `source_span_ref_id`.\n\n## Source Packet\n\n{src}\n"
    rel = f"# Live Graph Memory Extractor — Relation Pass\n\n{_safety_boundary()}\n\n{uncertainty}\n\nPass 2: using manually supplied observation JSON, propose relationship edges only. JSON section: `observation_edges`. Exhaustively extract origin, role, familial, location, allegiance, and combat_trait relationships supported by cited spans. Do not add new entities.\n"
    assembly = f"# Live Graph Memory Extractor — Assembly Pass\n\n{_safety_boundary()}\n\nPass 3: assemble the full output envelope from observation + relation JSON. No new facts. Preserve all beats and edges from prior passes unless merged with explicit note in `review_sidecar.notes`.\n\n{scaffold}\n\n{high_risk}\n"
    return {"observation_prompt.md": obs, "relation_prompt.md": rel, "assembly_prompt.md": assembly}


def build_prompt_packet_manifest(mode: str, verified: Mapping[str, Any], out_dir: Path | None = None) -> dict[str, Any]:
    b = verified["bundle"]
    rows = source_packet_rows(verified)
    return {
        "schema": PACKET_SCHEMA,
        "version": VERSION,
        "fixture_id": FIXTURE_ID,
        "mode": mode,
        "run_id": b["run_manifest"]["run_id"],
        "campaign_id": b["run_manifest"]["campaign_id"],
        "session_id": b["run_manifest"]["session_id"],
        "source": {
            "input_sha256": b["run_manifest"]["source"]["input_sha256"],
            "input_line_count": b["run_manifest"]["source"]["input_line_count"],
            "source_units": len(rows),
            "source_span_refs": [r["source_span_ref_id"] for r in rows],
        },
        "prompt_files": PROMPT_FILES[mode],
        "output_contract": {
            "target": ENVELOPE_SCHEMA,
            "required_sections": list(ENVELOPE_SECTIONS),
            "candidate_graph_sections": list(GRAPH_SECTIONS),
            "preview_only": True,
        },
        "safety": {
            "manual_llm_only": True,
            "no_api_key_required": True,
            "graph_writes_allowed": False,
            "query_execution_allowed": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scan_allowed": False,
            "corpus_mutation_allowed": False,
        },
        "out_dir": str(out_dir) if out_dir else None,
    }


def build_source_packet_summary(verified: Mapping[str, Any]) -> dict[str, Any]:
    rows = source_packet_rows(verified)
    b = verified["bundle"]
    return {
        "schema": SUMMARY_SCHEMA,
        "version": VERSION,
        "run_id": b["run_manifest"]["run_id"],
        "source_sha256": b["run_manifest"]["source"]["input_sha256"],
        "source_line_count": b["run_manifest"]["source"]["input_line_count"],
        "source_units": len(rows),
        "source_span_refs": [
            {
                "source_span_ref_id": r["source_span_ref_id"],
                "source_unit_id": r["source_unit_id"],
                "line_start": r["line_start"],
                "line_end": r["line_end"],
            }
            for r in rows
        ],
        "raw_full_text_included": False,
    }


def write_prompt_packet(mode: str, run_bundle: Path, source_recap: Path, out_dir: Path, *, allow_overwrite: bool = False) -> dict[str, Any]:
    target = validate_output_path(out_dir, allow_overwrite=allow_overwrite)
    verified = verify_run_bundle_and_source(run_bundle, source_recap)
    if target.exists() and any(target.iterdir()):
        _assert(allow_overwrite, "output_exists")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    prompts = render_prompts(mode, verified)
    manifest = build_prompt_packet_manifest(mode, verified, target)
    summary = build_source_packet_summary(verified)
    (target / "prompt_packet_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target / "source_packet_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, text in prompts.items():
        (target / name).write_text(text, encoding="utf-8")
    (target / "manual_run_notes.md").write_text(
        "# Manual Live Extractor Notes\n\n"
        "Paste prompts into a model manually. Save untrusted JSON as `candidate_output.json` "
        "(envelope with `candidate_graph` + `review_sidecar`). Validate with "
        "`validate_live_extractor_candidate_output` before review. No graph writes or promotion occur here.\n",
        encoding="utf-8",
    )
    return manifest


def load_manifest() -> dict[str, Any]:
    return _load_json(Path(MANIFEST_PATH))


def load_sample_packet_manifest() -> dict[str, Any]:
    return _load_json(Path(SAMPLE_PACKET_PATH))


def validate_prompt_manifest(m: Mapping[str, Any]) -> None:
    _assert(m.get("schema") == SCHEMA and m.get("version") == VERSION, "wrong_manifest_schema")
    _assert(m.get("fixture_id") == FIXTURE_ID, "wrong_fixture_id")
    _assert(set(m.get("modes", {})) == set(MODES), "wrong_modes")
    for mode in MODES:
        _assert(m["modes"][mode]["prompt_files"] == PROMPT_FILES[mode], f"bad_prompt_files:{mode}")
    for k, v in m.get("safety", {}).items():
        _assert(v is (k in {"manual_llm_only", "preview_only", "source_span_required"}), f"unsafe_manifest:{k}")


def validate_prompt_packet_manifest(p: Mapping[str, Any]) -> None:
    _assert(p.get("schema") == PACKET_SCHEMA and p.get("version") == VERSION, "wrong_packet_schema")
    _assert(p.get("mode") in MODES, "bad_packet_mode")
    _assert(p.get("prompt_files") == PROMPT_FILES[p["mode"]], "bad_packet_files")
    contract = p.get("output_contract", {})
    _assert(contract.get("target") == ENVELOPE_SCHEMA, "wrong_output_contract")
    _assert(set(ENVELOPE_SECTIONS) <= set(contract.get("required_sections", [])), "missing_envelope_sections")
    for k, v in p.get("safety", {}).items():
        _assert(v is (k in {"manual_llm_only", "no_api_key_required"}), f"unsafe_packet:{k}")


def validate_candidate_output(candidate: Mapping[str, Any], allowed_span_refs: set[str] | None = None, *, run_bundle: Path | None = None) -> dict[str, Any]:
    text = json.dumps(candidate, sort_keys=True)
    for tok in FORBIDDEN_OUTPUT_TOKENS:
        _assert(tok not in text, f"forbidden_candidate_output:{tok}")
    bundle = Path(run_bundle or SESSION_23_RUN_BUNDLE)
    try:
        return validate_live_candidate_output(candidate, run_bundle=bundle, allowed_span_refs=allowed_span_refs)
    except ValueError as exc:
        raise HarnessValidationError(str(exc)) from exc


def validate_all() -> None:
    validate_prompt_manifest(load_manifest())
    validate_prompt_packet_manifest(load_sample_packet_manifest())
    verified = verify_run_bundle_and_source(Path(SESSION_23_RUN_BUNDLE), Path(SESSION_23_SOURCE_RECAP))
    for mode in MODES:
        prompts = render_prompts(mode, verified)
        packet = build_prompt_packet_manifest(mode, verified)
        validate_prompt_packet_manifest(packet)
        joined = "\n".join(prompts.values())
        for needle in (
            "source_span_ref_id",
            "Do not resolve cliffhangers",
            "Named-in-span-A",
            "review_sidecar",
            "dmb_candidate_graph_preview_v0",
            "Forbidden: approve memory",
            "status` (must be `pending`",
        ):
            _assert(needle in joined, f"prompt_missing_text:{needle}")
