"""Canonical statblock selection, marker checks, intent classification, benchmark hooks.

Policy-driven: ``corpus_policy`` supplies ``canonical_statblock_relpath`` and optional
``mechanical_statblock_trace_path_filters`` for tool-trace matching (no hardcoded NPC).
Gold JSON supplies markers, expected CR, and optional **benchmark-only** post-planner checks
(see ``evaluate_step2_post_planner_benchmark`` and key ``planner_bridge`` in Step 2 gold).

See ``Docs/Plans/NAMING-benchmark-vs-runtime.md`` for benchmark vs runtime vocabulary.
"""

from __future__ import annotations

import copy
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from src.agent.corpus_path_tools import read_paths_from_tool_trace
from src.agent.synthesis import _load_api_key

IntentMode = Literal["factual_lookup", "upgrade_request", "comparison_request"]

PowerAxis = Literal["challenge_rating", "class_level", "hybrid", "unknown"]

SELECTION_RULE_POLICY_CANONICAL = "corpus_policy.canonical_statblock_relpath"


def _norm_rel(p: str) -> str:
    return p.strip().replace("\\", "/")


def select_canonical_statblock_relpath(policy: dict[str, Any]) -> str | None:
    raw = policy.get("canonical_statblock_relpath")
    if isinstance(raw, str) and raw.strip():
        return _norm_rel(raw)
    return None


def build_selection_reason(
    policy: dict[str, Any],
    *,
    outcome: str,
    canon: str | None = None,
) -> dict[str, Any]:
    """Machine-readable trace for why Step 2 picked (or failed to pick) a canonical statblock."""
    out: dict[str, Any] = {
        "rule_id": SELECTION_RULE_POLICY_CANONICAL,
        "outcome": outcome,
        "corpus_policy_schema": policy.get("schema"),
    }
    if policy.get("entity_canonical_name"):
        out["entity_canonical_name"] = policy.get("entity_canonical_name")
    if canon is not None:
        out["canonical_statblock_relpath"] = canon
    return out


def detail_for_cli_stdout(canonical_detail: dict[str, Any], max_extract_chars: int = 80_000) -> dict[str, Any]:
    """Replace huge ``extracted_markdown`` in a copy for terminal JSON."""
    d = copy.deepcopy(canonical_detail)
    em = d.get("extracted_markdown")
    if isinstance(em, str) and len(em) > max_extract_chars:
        d["extracted_markdown"] = (
            f"[{len(em)} characters omitted from CLI stdout; use run_step2_canonical_gates / run_step2_all in Python for full text]"
        )
        d["extracted_markdown_cli_truncated"] = True
    return d


def build_extracted_section_span(corpus_rel: str, extracted: str) -> dict[str, Any]:
    """
    Char offsets into the file as read (UTF-8 decoded ``str``). ``end_char`` is **exclusive**
    (Python slice ``extracted == full_body[start_char:end_char]`` when ``start_char == 0``).
    """
    n = len(extracted)
    return {
        "corpus_relative_path": _norm_rel(corpus_rel),
        "start_char": 0,
        "end_char": n,
        "end_char_exclusive": True,
        "length_chars": n,
    }


def parse_challenge_rating_from_statblock(text: str) -> int | None:
    m = re.search(r"Challenge\s+Rating\s*:\s*(\d+)", text, flags=re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))


@dataclass(frozen=True)
class IntentClassification:
    intent_mode: IntentMode
    power_axis: PowerAxis
    clarifier_required: bool
    clarifier_question: str

    def matches_expect(self, expect: dict[str, Any]) -> tuple[bool, list[str]]:
        diffs: list[str] = []
        for key in ("intent_mode", "power_axis", "clarifier_required"):
            if key not in expect:
                continue
            a = getattr(self, key)
            b = expect[key]
            if a != b:
                diffs.append(f"{key}: got {a!r}, expected {b!r}")
        return len(diffs) == 0, diffs


_INTENT_CLASSIFIER_MODEL_ENV = "NPC_INTENT_CLASSIFIER_MODEL"
_INTENT_POLICY_ACTION = "npc_intent_classifier"
_DEFAULT_INTENT_CLASSIFIER_MODEL = "gpt-4o-mini"

_INTENT_CLASSIFIER_INSTRUCTIONS = """You classify one GM user line about an NPC (statblock, CR, class levels, prep).
Return ONLY one JSON object (no markdown fences, no other text). Keys:
- intent_mode: "factual_lookup" | "upgrade_request" | "comparison_request"
- power_axis: "challenge_rating" | "class_level" | "hybrid" | "unknown"
- clarifier_required: boolean
- clarifier_question: string ("" when clarifier_required is false; otherwise one short question)

Definitions:
- factual_lookup: asking what a stat/CR/AC/HP/level IS now, without asking you to change or regenerate the sheet.
- upgrade_request: wants a stronger or new statblock, CR bump, level-up, regenerate sheet, rebuild from dossier, export for a higher tier, etc.
- comparison_request: compares two entities, builds, or sheets.

If the line mixes prep/research tone with "level up" or power increase without saying CR vs class, use upgrade_request, power_axis unknown, clarifier_required true.
"""


def _resolve_intent_classifier_model(model: str | None) -> str:
    """
    Order: explicit ``model``, env ``NPC_INTENT_CLASSIFIER_MODEL``, then Buddy ``MODEL_POLICY.json``
    action ``npc_intent_classifier`` (else ``structured_generation`` role) → ``models`` entry,
    else ``models.cheapest``, else ``gpt-4o-mini``.
    """
    if model and str(model).strip():
        return str(model).strip()
    env_model = os.environ.get(_INTENT_CLASSIFIER_MODEL_ENV, "").strip()
    if env_model:
        return env_model
    from src.model_policy import load_buddy_model_policy

    policy = load_buddy_model_policy()
    if policy:
        models = policy.get("models") or {}
        actions = policy.get("actions") or {}
        role = actions.get(_INTENT_POLICY_ACTION) or actions.get("structured_generation")
        if isinstance(role, str) and role.strip():
            mid = models.get(role.strip())
            if isinstance(mid, str) and mid.strip():
                return mid.strip()
        cheapest = models.get("cheapest")
        if isinstance(cheapest, str) and cheapest.strip():
            return cheapest.strip()
    return _DEFAULT_INTENT_CLASSIFIER_MODEL


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*", "", t)
        if "```" in t:
            t = t.rsplit("```", 1)[0]
    return t.strip()


_VALID_INTENT_MODES: frozenset[str] = frozenset(
    {"factual_lookup", "upgrade_request", "comparison_request"}
)
_VALID_POWER_AXES: frozenset[str] = frozenset(
    {"challenge_rating", "class_level", "hybrid", "unknown"}
)


def _intent_classification_from_payload(obj: dict[str, Any]) -> IntentClassification:
    im = obj.get("intent_mode")
    if im not in _VALID_INTENT_MODES:
        im = "factual_lookup"
    pa = obj.get("power_axis")
    if pa not in _VALID_POWER_AXES:
        pa = "unknown"
    clar = bool(obj.get("clarifier_required"))
    q = str(obj.get("clarifier_question") or "").strip()
    if clar and not q:
        q = "Should this use CR-based NPC math, class-style levels, or both?"
    if not clar:
        q = ""
    return IntentClassification(
        intent_mode=im,  # type: ignore[arg-type]
        power_axis=pa,  # type: ignore[arg-type]
        clarifier_required=clar,
        clarifier_question=q,
    )


def _intent_classification_from_gold_expect(expect: dict[str, Any]) -> IntentClassification:
    """Build classification from Step 2 gold ``expect`` (for fixture-sequence test clients)."""
    im = expect.get("intent_mode", "factual_lookup")
    if im not in _VALID_INTENT_MODES:
        im = "factual_lookup"
    pa = expect.get("power_axis", "unknown")
    if pa not in _VALID_POWER_AXES:
        pa = "unknown"
    clar = bool(expect.get("clarifier_required"))
    q = str(expect.get("clarifier_question") or "").strip()
    if clar and not q:
        q = "Should this use CR-based NPC math, class-style levels, or both?"
    if not clar:
        q = ""
    return IntentClassification(
        intent_mode=im,  # type: ignore[arg-type]
        power_axis=pa,  # type: ignore[arg-type]
        clarifier_required=clar,
        clarifier_question=q,
    )


def _intent_json_from_classification(c: IntentClassification) -> str:
    return json.dumps(
        {
            "intent_mode": c.intent_mode,
            "power_axis": c.power_axis,
            "clarifier_required": c.clarifier_required,
            "clarifier_question": c.clarifier_question,
        },
        ensure_ascii=False,
    )


class _FakeIntentResponse:
    __slots__ = ("id", "output_text", "model")

    def __init__(self, output_text: str) -> None:
        self.id = "fake-intent-response"
        self.output_text = output_text
        self.model = "fake-intent-model"


class SequenceIntentClassifierClient:
    """
    Test double: ``client.responses.create`` returns queued JSON bodies in order.

    Use ``build_step2_intent_fixture_sequence_client`` for gold-driven queues, or construct
    directly for custom sequences.
    """

    def __init__(self, json_texts: list[str]) -> None:
        self._json_texts = list(json_texts)
        self._i = 0
        self.responses = self._Responses(self)

    class _Responses:
        def __init__(self, outer: SequenceIntentClassifierClient) -> None:
            self._outer = outer

        def create(self, **kwargs: Any) -> _FakeIntentResponse:
            o = self._outer
            if o._i >= len(o._json_texts):
                raise RuntimeError("SequenceIntentClassifierClient: no more queued responses")
            body = o._json_texts[o._i]
            o._i += 1
            return _FakeIntentResponse(body)


def build_step2_intent_fixture_sequence_client(step2_gold: dict[str, Any]) -> SequenceIntentClassifierClient:
    """Fake OpenAI client: one ``responses.create`` JSON per ``step2_gold.fixtures`` row (order preserved)."""
    seq: list[str] = []
    for fx in step2_gold.get("fixtures") or []:
        ex = fx.get("expect") or {}
        seq.append(_intent_json_from_classification(_intent_classification_from_gold_expect(ex)))
    return SequenceIntentClassifierClient(seq)


def intent_client_for_gold_expect(expect: dict[str, Any]) -> SequenceIntentClassifierClient:
    """Single-response fake client returning JSON for one gold-style ``expect`` dict."""
    c = _intent_classification_from_gold_expect(expect)
    return SequenceIntentClassifierClient([_intent_json_from_classification(c)])


def classify_intent(
    user_line: str,
    *,
    client: Any | None = None,
    model: str | None = None,
) -> IntentClassification:
    """
    One OpenAI ``responses.create`` call (cheap model from ``MODEL_POLICY.json`` by default).

    Tests and offline harnesses should pass ``client=`` (e.g.
    ``build_step2_intent_fixture_sequence_client``). With ``client=None``, ``OPENAI_API_KEY`` is required.
    """
    text = user_line.strip()
    if not text:
        return IntentClassification(
            intent_mode="factual_lookup",
            power_axis="unknown",
            clarifier_required=False,
            clarifier_question="",
        )
    mid = _resolve_intent_classifier_model(model)
    if client is None:
        api_key = _load_api_key()
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for classify_intent unless you pass client=... "
                "(use build_step2_intent_fixture_sequence_client in tests)."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package is required for classify_intent.") from exc
        client = OpenAI(api_key=api_key)
    create_fn = getattr(getattr(client, "responses", None), "create", None)
    if create_fn is None:
        raise TypeError("client must have responses.create (OpenAI Responses API).")
    response = create_fn(
        model=mid,
        instructions=_INTENT_CLASSIFIER_INSTRUCTIONS,
        input=[{"type": "message", "role": "user", "content": text}],
    )
    out = (getattr(response, "output_text", None) or "").strip()
    if not out:
        raise RuntimeError("Intent classifier model returned empty output_text.")
    try:
        payload = json.loads(_strip_json_fence(out))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Intent classifier returned non-JSON: {out[:500]!r}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Intent classifier JSON must be an object, got {type(payload).__name__}")
    return _intent_classification_from_payload(payload)


def run_step2_canonical_gates(
    corpus_dir: Path,
    *,
    corpus_policy: dict[str, Any],
    step2_gold: dict[str, Any],
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    Returns ``(detail, ok, violations)``.

    ``corpus_policy`` and ``step2_gold`` must be provided (benchmark loads JSON).
    """
    g2 = step2_gold
    violations: list[str] = []

    canon = select_canonical_statblock_relpath(corpus_policy)
    if not canon:
        violations.append("G2.1 FAIL: corpus_policy.canonical_statblock_relpath is missing or empty")
        return {
            "canonical_path": None,
            "selection_reason": build_selection_reason(corpus_policy, outcome="policy_field_missing_or_empty"),
        }, False, violations

    root = corpus_dir.resolve()
    abs_path = (root / canon).resolve()
    try:
        abs_path.relative_to(root)
    except ValueError:
        violations.append(f"G2.1 FAIL: canonical path escapes corpus root: {canon}")
        return {
            "canonical_path": canon,
            "selection_reason": build_selection_reason(
                corpus_policy, outcome="path_escapes_corpus_root", canon=canon
            ),
        }, False, violations

    if not abs_path.is_file():
        violations.append(f"G2.1 FAIL: canonical statblock file missing on disk: {canon}")
        return {
            "canonical_path": canon,
            "selection_reason": build_selection_reason(corpus_policy, outcome="file_not_found", canon=canon),
        }, False, violations

    try:
        body = abs_path.read_text(encoding="utf-8")
    except OSError as e:
        violations.append(f"G2.1 FAIL: could not read canonical statblock ({canon}): {e}")
        return {
            "canonical_path": canon,
            "selection_reason": build_selection_reason(corpus_policy, outcome="read_error", canon=canon),
        }, False, violations

    max_c = g2.get("detail_max_extracted_markdown_chars")
    truncated = False
    if max_c is not None:
        try:
            lim = int(max_c)
        except (TypeError, ValueError):
            lim = 0
        if lim > 0 and len(body) > lim:
            extracted = body[:lim]
            truncated = True
        else:
            extracted = body
    else:
        extracted = body

    markers = [str(m) for m in (g2.get("required_statblock_markers") or []) if str(m).strip()]
    for m in markers:
        if m not in body:
            violations.append(f"G2.2 FAIL: required statblock marker not found in canonical file: {m!r}")

    exp_cr = g2.get("expected_challenge_rating")
    parsed = parse_challenge_rating_from_statblock(body)
    detail: dict[str, Any] = {
        "canonical_path": canon,
        "selection_reason": build_selection_reason(corpus_policy, outcome="selected", canon=canon),
        "extracted_markdown": extracted,
        "extracted_section_span": build_extracted_section_span(canon, extracted),
        "parsed_challenge_rating": parsed,
        "expected_challenge_rating": exp_cr,
        "markers_required": markers,
        "markers_found": {m: (m in body) for m in markers},
    }
    if truncated:
        detail["extracted_markdown_truncated"] = True
        detail["extracted_markdown_full_file_chars"] = len(body)

    if parsed is None:
        violations.append("G2.2b FAIL: could not parse Challenge Rating from canonical statblock")
    elif exp_cr is not None and int(exp_cr) != parsed:
        violations.append(f"G2.2b FAIL: parsed CR {parsed} != gold expected_challenge_rating {exp_cr}")

    return detail, len(violations) == 0, violations


def run_step2_intent_fixture_gates(
    *,
    step2_gold: dict[str, Any],
    client: Any | None = None,
    model: str | None = None,
) -> tuple[bool, list[str]]:
    """Evaluate G2.4.* expectations for each gold fixture (LLM or injected ``client``)."""
    g2 = step2_gold
    violations: list[str] = []
    for fx in g2.get("fixtures") or []:
        fid = str(fx.get("id", "?"))
        ul = str(fx.get("user_line", "")).strip()
        expect = fx.get("expect") or {}
        if not ul:
            violations.append(f"G2.4 FAIL [{fid}]: empty user_line")
            continue
        got = classify_intent(ul, client=client, model=model)
        ok, diffs = got.matches_expect(expect)
        if not ok:
            for d in diffs:
                violations.append(f"G2.4 FAIL [{fid}]: {d}")
        if bool(expect.get("clarifier_required")) and not got.clarifier_required:
            violations.append(f"G2.4.3 FAIL [{fid}]: expected clarifier_required True, got False")
        if bool(expect.get("clarifier_required")) and not str(got.clarifier_question).strip():
            violations.append(f"G2.4.3 FAIL [{fid}]: clarifier_required but clarifier_question empty")
        if not bool(expect.get("clarifier_required")) and got.clarifier_required:
            violations.append(f"G2.4.3 FAIL [{fid}]: expected clarifier_required False, got True")

    return len(violations) == 0, violations


def run_step2_all(
    corpus_dir: Path,
    *,
    corpus_policy: dict[str, Any],
    step2_gold: dict[str, Any],
    intent_client: Any | None = None,
    intent_model: str | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """Canonical gates + intent fixture gates."""
    all_v: list[str] = []
    detail, ok_c, v_c = run_step2_canonical_gates(
        corpus_dir, corpus_policy=corpus_policy, step2_gold=step2_gold
    )
    all_v.extend(v_c)
    ok_i, v_i = run_step2_intent_fixture_gates(
        step2_gold=step2_gold, client=intent_client, model=intent_model
    )
    all_v.extend(v_i)
    out = {"canonical_detail": detail, "intent_fixtures_ok": ok_i}
    return out, ok_c and ok_i, all_v


def statblock_trace_reads_matching_policy(read_paths: list[str], policy: dict[str, Any]) -> list[str]:
    """
    Paths (from ``read_corpus_file`` or ``load_context_markdown`` traces) that count as this entity’s
    mechanical statblock for the post-planner Step 2 benchmark trace checks.

    Controlled by ``corpus_policy.mechanical_statblock_trace_path_filters``:

    - ``all_substrings_ignore_case`` (list[str]): every entry must appear as a substring of the path
      (case-insensitive).
    - ``path_suffix_ignore_case`` (str, optional): if set, path must end with this suffix (default ``.md``).

    If filters are missing or ``all_substrings_ignore_case`` is empty, returns ``[]`` (the benchmark
    does not infer entity statblock reads from the trace).
    """
    raw = policy.get("mechanical_statblock_trace_path_filters")
    if not isinstance(raw, dict):
        return []
    subs = [str(x).strip() for x in (raw.get("all_substrings_ignore_case") or []) if str(x).strip()]
    if not subs:
        return []
    sfx_raw = raw.get("path_suffix_ignore_case")
    sfx = ".md" if sfx_raw is None else str(sfx_raw).strip().lower()
    if not sfx:
        sfx = ".md"
    out: list[str] = []
    for p in read_paths:
        n = _norm_rel(p).lower()
        if not all(s.lower() in n for s in subs):
            continue
        if not n.endswith(sfx):
            continue
        out.append(_norm_rel(p))
    return out


def evaluate_step2_post_planner_benchmark(
    *,
    user_message: str,
    tool_trace: list[dict[str, Any]],
    planner_scenario_key: str,
    corpus_policy: dict[str, Any],
    step2_gold: dict[str, Any],
    intent_client: Any | None = None,
    intent_model: str | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    **Benchmark / observation only** — runs **after** a planner turn for scoring and CI.

    Classifies ``user_message`` (same string the planner saw) and optionally compares to gold
    ``intent_expectations_by_planner_scenario_key``. Optionally asserts statblock paths read in
    ``tool_trace`` include ``corpus_policy.canonical_statblock_relpath`` when policy filters match.

    This does **not** change planner instructions, tool registration, or live routing; harnesses
    merge violations into ``LiveEvalResult`` under the legacy key ``step2_bridge``.

    ``step2_gold["planner_bridge"]`` (optional). If absent or empty, returns ``({}, True, [])``.
    The JSON key ``planner_bridge`` is a historical name for this **benchmark config** block.
    """
    g2 = step2_gold
    cfg = g2.get("planner_bridge")
    if not isinstance(cfg, dict) or not cfg:
        return {}, True, []

    violations: list[str] = []
    detail: dict[str, Any] = {"planner_scenario_key": planner_scenario_key}

    expect_map = cfg.get("intent_expectations_by_planner_scenario_key") or {}
    expect = expect_map.get(planner_scenario_key) if isinstance(expect_map, dict) else None
    got = classify_intent(user_message, client=intent_client, model=intent_model)
    detail["intent_from_planner_user_message"] = {
        "intent_mode": got.intent_mode,
        "power_axis": got.power_axis,
        "clarifier_required": got.clarifier_required,
    }

    if isinstance(expect, dict) and expect:
        ok_m, diffs = got.matches_expect(expect)
        if not ok_m:
            for d in diffs:
                violations.append(f"BENCHMARK intent [{planner_scenario_key}]: {d}")
        if "clarifier_required" in expect:
            if bool(expect.get("clarifier_required")) and not got.clarifier_required:
                violations.append(
                    f"BENCHMARK intent [{planner_scenario_key}]: expected clarifier_required True, got False"
                )
            if bool(expect.get("clarifier_required")) and not str(got.clarifier_question).strip():
                violations.append(
                    f"BENCHMARK intent [{planner_scenario_key}]: clarifier_required but clarifier_question empty"
                )
            if not bool(expect.get("clarifier_required")) and got.clarifier_required:
                violations.append(
                    f"BENCHMARK intent [{planner_scenario_key}]: expected clarifier_required False, got True"
                )

    if cfg.get("assert_statblock_read_matches_canonical_when_present"):
        canon = select_canonical_statblock_relpath(corpus_policy)
        trace_paths = read_paths_from_tool_trace(tool_trace)
        reads = statblock_trace_reads_matching_policy(trace_paths, corpus_policy)
        detail["mechanical_statblock_reads_in_trace"] = reads
        detail["canonical_statblock_relpath"] = canon
        if reads and canon:
            cn = _norm_rel(canon).lower()
            read_lower = {_norm_rel(p).lower() for p in reads}
            if cn not in read_lower:
                violations.append(
                    "BENCHMARK trace: mechanical statblock read(s) "
                    f"{reads!r} but corpus_policy.canonical_statblock_relpath "
                    f"{_norm_rel(canon)!r} was never opened."
                )

    return detail, len(violations) == 0, violations
