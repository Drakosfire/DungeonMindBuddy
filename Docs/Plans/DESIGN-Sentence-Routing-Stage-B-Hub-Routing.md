# Design — `route_sentence_units_to_hubs` (legacy: Stage B): sentence unit → hub routing

**Date:** 2026-04-25  
**Status:** Design (implementation: **hub-routing runner** `step2_route_run.py` + `gold_routing` + `collect_stage_b_violations`; legacy artifact prefix `sentence_routing_stage_b_*`)  
**Parent roadmap:** `Docs/Plans/PLAN-Sentence-Routing-Stages-B-through-D.md`  
**Guardrails:** `Docs/Plans/GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md`

**Vocabulary:** In prose, use explicit names:

- `capture_sentence_units` (legacy: Stage A)
- `route_sentence_units_to_hubs` (legacy: Stage B — this document)
- `propose_new_hubs_from_unmapped_units` (legacy: Stage C)
- `assemble_hub_scoped_retrieval_context` (legacy: Stage D)

JSON keys and filenames may still say `stage_a` / `stage_b` / `sentence_routing_stage_*` for compatibility.

---

## 1. Purpose

`route_sentence_units_to_hubs` answers one question only:

> Given **verified sentence units** from `capture_sentence_units` and a **closed list of hubs**, which hubs does each unit belong to for continuity / retrieval — if any?

It does **not**:

- invent new hubs (that is `propose_new_hubs_from_unmapped_units`, legacy Stage C),
- compress prose into timelines/dossiers (`assemble_hub_scoped_retrieval_context`, legacy Stage D / projections),
- prove full recap coverage (`capture_sentence_units` + optional coverage matrix can do that separately).

---

## 2. Inputs

### 2.1 Required from `capture_sentence_units` (legacy: Stage A)

Each `sentence_unit`:


| Field                    | Type   | Meaning                                                                    |
| ------------------------ | ------ | -------------------------------------------------------------------------- |
| `unit_id`                | string | Stable id from capture (e.g. `u-L0003-01`)                                 |
| `path`                   | string | Corpus-relative recap path (same as scenario `recap_relative_path` for v0) |
| `line_start`, `line_end` | int    | Inclusive 1-based lines into recap file                                    |
| `text`                   | string | Unit text (trimmed segment)                                                |


`route_sentence_units_to_hubs` consumes **either**:

- inline `sentence_units` array inside the scenario JSON (tests only), or
- a **`capture_sentence_units` sidecar** JSON field `sentence_units` (production path), or
- recomputed units from `--corpus-root` + `recap_relative_path` (deterministic replay).

### 2.2 Required from scenario `input`


| Field                    | Required | Meaning                                                        |
| ------------------------ | -------- | -------------------------------------------------------------- |
| `hub_manifest`           | yes      | Closed list of routable hubs (see §3)                          |
| `recap_relative_path`    | yes      | Same recap `capture_sentence_units` used                         |
| `corpus_root`            | optional | Defaults to repo root for synthetic; real runs use corpus root |
| `campaign_id`, `session` | optional | Metadata for telemetry + future multi-campaign manifests       |


### 2.3 Optional harness context (v2)

- `known_character_slugs` — same strings as manifest slugs, redundant if manifest complete; useful for prompt clarity only.
- `routing_hints` — **machine-only** structured hints (e.g. “units on lines 5–8 often involve hub X”) for adversarial scenarios; not GM-facing prose.

---

## 3. Hub manifest (allowlist)

### 3.1 Shape

Ordered JSON array (order = display order in prompt, not priority):

```json
{
  "slug": "captain_lysandra_ironveil",
  "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md",
  "subject_class": "npc",
  "campaign_id": "longmont-c2",
  "label": "Captain Lysandra Ironveil (C2 hub README)"
}
```

**Fields:**


| Field           | Required    | Notes                                                                                                                                         |
| --------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `slug`          | yes         | Unique within manifest; must match `^[a-z0-9_]+$` (same discipline as participants elsewhere)                                                 |
| `path`          | yes         | Corpus-relative path to a **real** hub anchor file (README, timeline, or agreed anchor); used for provenance + future “open this hub” tooling |
| `subject_class` | yes         | Closed vocab: `npc`, `pc`, `location`, `faction`, `session`, `campaign`, `item`, `event`, `world`                                             |
| `campaign_id`   | recommended | Disambiguation when same slug exists in two campaigns                                                                                         |
| `label`         | optional    | Short human-readable string for prompt tables only                                                                                            |


### 3.2 Validation (runner, fail-closed before LLM)

1. **Unique slugs** — duplicate slug → abort run with violation.
2. **Path exists** under `corpus_root` when `validate_manifest_paths: true` (default true for real corpus; false for pure synthetic fixtures that use fake paths only in **unit tests** of the grader).
3. `**subject_class`** in closed vocab.
4. **Size cap** — e.g. `max_manifest_entries: 64` default; prevents prompt blow-up and forces scenario authors to scope hubs to the session.

### 3.3 Relationship to “discovery” rules

- **Product / planner** flows must not provision per-task recap navigation in the user channel (see `.cursor/rules/llm-context-discovery.mdc`).
- **This benchmark** may inject the manifest as a **structured block in the harness-built instruction payload** (same moral category as eval `detail` blobs): it is not simulating a GM ask; it is the grading contract.

---

## 4. Model output (strict JSON)

### 4.1 Top-level envelope

```json
{
  "schema": "sentence_hub_routes_v1",
  "routes": [ /* RouteRow */ ]
}
```

### 4.2 `RouteRow` (one per `unit_id` from `capture_sentence_units`)


| Field                     | Type     | Required | Meaning                                                                   |
| ------------------------- | -------- | -------- | ------------------------------------------------------------------------- |
| `unit_id`                 | string   | yes      | Must match a `capture_sentence_units` unit exactly                        |
| `assigned_hubs`           | string[] | yes      | Subset of manifest slugs; may be empty                                    |
| `confidence`              | string   | yes      | One of `high`, `medium`, `low` (ordered for thresholds)                   |
| `rationale`               | string   | yes      | One or two sentences, **grounded in unit text** (quote fragments allowed) |
| `needs_new_hub_candidate` | boolean  | yes      | True iff model believes no manifest hub fits but the beat is real         |


**Hard constraints (validator rejects parse / runner marks FAIL):**

1. Every element of `assigned_hubs` ∈ manifest slug set.
2. **No duplicate slugs** inside `assigned_hubs` for one row.
3. **Exactly one `RouteRow` per `unit_id`** from `capture_sentence_units` (no missing, no extras).
4. If `assigned_hubs` is non-empty, `needs_new_hub_candidate` must be **false**.
5. If `needs_new_hub_candidate` is **true**, `assigned_hubs` must be **empty** (forces `propose_new_hubs_from_unmapped_units` to own “new hub” intent).

**Confidence policy (for `propose_new_hubs_from_unmapped_units` / telemetry only in v1):**

- `low` or `needs_new_hub_candidate` → eligible for proposals (when gold expects proposals).
- `high`/`medium` → not proposal-eligible unless gold overrides.

---

## 5. Prompt design (behavioral contract)

### 5.1 System message (standing rules)

Content themes (exact wording left to implementation):

1. You receive a **closed list** of hubs; any slug not listed is forbidden.
2. **Multi-label is allowed** when the unit genuinely implicates multiple hubs.
3. Prefer **abstain** (empty `assigned_hubs` + `needs_new_hub_candidate` true **only** when appropriate) over wrong attachment; wrong hub is worse than unknown.
4. **Rationale must cite** phrases from the unit text (substring match check optional in v2).
5. Do not restate the entire recap; only use each `text` field.
6. Output **only** the JSON envelope; no markdown fences.

### 5.2 User / harness payload (per run)

Structured sections:

1. `campaign_id`, `session`, `recap_relative_path` (metadata).
2. `hub_manifest` table (slug, label, subject_class, path).
3. `sentence_units` array (unit_id, line_start/end, text).

No free-form GM question in v1 harness (optional v2: add a synthetic “planning intent” string to stress relevance).

---

## 6. Gold: `gold_routing` (grading contract)

### 6.1 Structure

```json
{
  "must_route": [
    {
      "unit_id": "u-L0003-01",
      "expected_hubs": ["npc_a", "location_town"],
      "max_extra_hubs": 1
    }
  ],
  "must_abstain": [
    {
      "unit_id": "u-L0005-02",
      "max_assigned_hubs": 0,
      "needs_new_hub_candidate": false
    }
  ],
  "soft_limits": {
    "max_mean_assigned_hubs_per_unit": 2.5,
    "max_unresolved_fraction": 0.2
  }
}
```

### 6.2 `must_route` semantics (hard)

For each gold row `g`:

- Find route row `r` with `r.unit_id == g.unit_id`.
- **Subset gate:** `set(g.expected_hubs) ⊆ set(r.assigned_hubs)`.
- **Over-route gate:** if `max_extra_hubs` is set,  
`len(r.assigned_hubs) <= len(g.expected_hubs) + g.max_extra_hubs`.
- If any check fails → violation `B1: must_route unit {id} …`.

### 6.3 `must_abstain` semantics (hard)

For each gold row `g`:

- `r.assigned_hubs` must satisfy `len(r.assigned_hubs) <= g.max_assigned_hubs` (typically 0).
- If `needs_new_hub_candidate` specified as false in gold, assert `r.needs_new_hub_candidate == false`.

Use abstain rows to catch **hallucinated attachment** to a convenient hub.

### 6.4 Soft limits (soft / telemetry-first in v1)

- Compute `mean_assigned_hubs_per_unit`, `fraction_unresolved` (empty assign + candidate false).
- If outside `soft_limits`, emit **telemetry warning**; promote to **hard** only after baseline cohort exists (per guardrails: no threshold without measurement).

### 6.5 Alternate matchers (optional)

If `unit_id` is brittle across capture tweaks, allow gold:

```json
{ "match": { "line_start": 3, "index_on_line": 1 }, "expected_hubs": ["..."] }
```

Harness calls ``normalize_gold_routing_matches`` in ``grader.py`` to resolve ``match`` → ``unit_id`` before ``collect_stage_b_violations``. Prefer explicit ``unit_id`` once `capture_sentence_units` output is frozen; use ``match`` for real recaps when capture line splits may drift slightly.

### 6.6 PC-only campaign scenarios (C1/C2 recap gates)

When the hub manifest lists **PC hubs only** for a session recap:

1. **Named / implicated PCs** — `must_route` expects every PC the unit implicates in **any role** (actor, object, addressee, rescuer, listener, swarm target, etc.), not only the grammatical subject. This catches “missing affected PC” failures that a subject-only heuristic would miss.
2. **Whole-party references** — after the recap has established the party roster, lines that refer to the party with **team** / **teammates** in a fight or shared job, or **first combat** + **team** language, may be graded as **must_route to all PCs** in that roster. **The group** may also be **must_route to all PCs** when the PCs are the **joint subject** of movement or approach in that unit (shared advance, arrival, or being led together). Use **must_abstain** when **the group** is only vague framing or the sentence center is not the party acting together (see `scenario_c1_session1_pc.json` `scenario_notes` for Session 1 L20/L22 vs generic cases).
3. **Pronouns and continuation** — when a prior unit names a focal PC and a following unit continues **the same PC’s** beat with pronouns only, gold may **must_route** that PC. Do **not** treat every pronoun after a PC mention as that PC: if the clause shifts subject to another named or clearly implied NPC (e.g. “she” = a local NPC the sentence defines), use **must_abstain** for PC hubs unless a PC is named again in the unit.
4. **`must_abstain` + out-of-manifest names** — rows with `max_assigned_hubs: 0` still forbid PC attachment. For units that name **NPCs or locations outside the PC manifest**, authors may **omit** `needs_new_hub_candidate: false` so a model that flags a real Stage-C candidate is not failed on B2 solely for `needs_new_hub_candidate: true`. Keep `needs_new_hub_candidate: false` on **purely generic** units to preserve abstain pressure (`scenario_c1_session2_pc.json` pattern).

---

## 7. Grader API

`normalize_gold_routing_matches(gold_routing, sentence_units) -> tuple[dict, list[str]]` — resolve ``match`` rows (§6.5); fatal strings in the errors list should become harness violations before routing gates.

`collect_stage_b_violations(routes, gold_routing, manifest_slugs=..., expected_unit_ids=...) -> tuple[list[str], dict]`

**Checks (ordered):**

1. **B0 schema** — top-level keys, one row per unit_id, no unknown unit_ids.
2. **B0b allowlist** — every assigned hub ∈ manifest.
3. **B0c row logic** — hub nonempty xor candidate rules from §4.
4. **B1 must_route** — §6.2.
5. **B2 must_abstain** — §6.3.
6. **B3 soft** — §6.4.

Telemetry (always):

- `routes_row_count`, `mean_assigned_hubs`, `unresolved_fraction`
- histogram `assigned_hubs_count_by_unit` (optional compact form)
- `needs_new_hub_candidate_count`

---

## 8. `route_sentence_units_to_hubs` hub-routing runner (CLI module `step2_route_run.py`)

### 8.1 CLI


| Flag              | Meaning                                                                                                                                                    |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--scenario-json` | Gold scenario path                                                                                                                                         |
| `--corpus-root`   | Root for recap + manifest path checks                                                                                                                      |
| `--prior-json`    | **`capture_sentence_units` sidecar** JSON (`sentence_routing_stage_a_capture--…` / `last_sentence_routing_stage_a_capture.json`); if omitted, re-run capture inline |
| `--model`         | Override model id                                                                                                                                          |
| `--no-llm`        | Read `fixture_routes` from scenario for CI / grader tests only                                                                                             |
| `--n`             | Cohort size (default 1). When **N > 1**, repeats the run and writes ``sentence_routing_stage_b_cohort_summary--<model>--N<n>--<UTC>.{json,md}`` (stderr prints cohort paths). |
| `--no-writes`     | Stdout-only mode (optional); skips per-run sidecars and cohort summaries.                                                                                  |


### 8.2 Sidecar JSON (written to `artifacts/runs/…`)

Fields (minimum):

- `schema`, `scenario_id`, `pass`, `violations` `{ "stage_b": [...] }`
- `telemetry` (merge `capture_sentence_units` replay telemetry + routing telemetry)
- `sentence_units` (echo or hash of input for diffability)
- `hub_manifest` (echo)
- `routes` (model output)
- `scenario_estimated_cost_usd` (from usage when LLM ran; `0` when `--no-llm`)

### 8.3 Model call

- Use same OpenAI client pattern as other evals: `load_dungeonmindbuddy_dotenv()`, `OpenAI()`, structured parse with Pydantic `RoutesEnvelope`.
- **Cost:** record `scenario_estimated_cost_usd`; cohort summaries follow `cost-as-signal.mdc`.

---

## 9. Failure modes (explicit)


| Symptom                        | Likely cause                       | Grader / next action                                                     |
| ------------------------------ | ---------------------------------- | ------------------------------------------------------------------------ |
| Wrong hub attached             | manifest too coarse / prompt drift | tighten must_abstain; expand manifest; prompt “wrong worse than abstain” |
| Over-route                     | multi-label too loose              | lower `max_extra_hubs`; add must_abstain near ambiguous units            |
| Under-route (missing expected) | model too shy                      | must_route rows; check rationale gate later                              |
| Schema invalid                 | model drift                        | strict parse; fail closed                                                |
| Extra route rows               | model added ids                    | B0: unit set mismatch                                                    |
| Candidate spam                 | model marks candidate often        | soft limit + proposals-stage rate gate                                   |


---

## 10. Testing strategy

1. **Deterministic grader tests** — build synthetic `routes` + `gold_routing` in pytest; no API.
2. **Fixture `--no-llm`** — scenario embeds `fixture_routes` for CI green path.
3. **Live smoke** (optional, manual or nightly) — one real model call; artifact on disk; cost recorded.

---

## 11. Open questions (resolve before first real-recap scenario)

1. **Anchor file in manifest:** README-only vs `timeline.md` allowed as routable surface? **(v1 template:** README paths only, matching current slice examples.)
2. **Session hub:** do we add synthetic `session`/`campaign` rows to manifest for beats that are “about the table” but not an NPC?
3. **Rationale enforcement:** substring check vs none in v1? **(v1:** not enforced in grader; prompt-only.)
4. **Cross-campaign slugs:** manifest must include `campaign_id` and grader checks consistency with scenario `campaign_id`. **(Not implemented yet** — rely on unique slugs per scenario until a grader check lands.)

---

## 12. Implementation checklist (engineering)

- Pydantic: `HubManifestEntry`, `RouteRow`, `RoutesEnvelope` (`route_schema.py`)
- `collect_stage_b_violations` in `grader.py`
- **`route_sentence_units_to_hubs` runner** (`step2_route_run.py`) with artifact writer + `--no-llm`
- Extend `scenario_mini.json` with manifest + `gold_routing` + optional `fixture_routes`
- `tests/test_sentence_routing_stage_b_grader.py`
- README section for `route_sentence_units_to_hubs`

When this checklist is complete, `route_sentence_units_to_hubs` is **designed and landed** for synthetic gold; real-recap scenarios are a separate promotion step.