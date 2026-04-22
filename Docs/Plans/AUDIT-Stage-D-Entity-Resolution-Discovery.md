# Stage D — NPC Entity Resolution: Discovery Audit (Read-Only)

**Date:** 2026-04-22  
**Author:** Read-only exploration subagent, dispatched after Stage C C1 cohorts shipped (commit `d937714`)  
**Scope:** Pre-design audit. No code, no commits. Output is a single dense report to ground the design conversation for Stage D.

---

## 1. Stage D's job, contracted

### Input contract (what Stage C hands off)

`StageCOutput` is three arrays, validated in the runner and graded in `grade_stage_c` (`evals/stage_c_npc_candidates_vertical_slice/step1_stage_c_run.py:83-86`):

- `tracked_npcs_active[]` — `{ slug, evidence_event_indices[], appearance_count }`
- `new_npc_candidates[]` — `{ descriptor, suggested_slug, evidence_event_indices[], rationale }`
- `unresolved_descriptors[]` — `{ descriptor, evidence_event_indices[], rationale }`

The system prompt defines semantics and the "only from `participants[]` ∪ `referenced_slugs[]`" rule (`step1_stage_c_run.py:145-193`). Stage D **inherits the same event JSON and registry** as Stage C (and typically the same PC roster), plus **all three buckets** as its resolution substrate.

**Stage C recall logic Stage D will extend:** NC3 requires every `tracked`/`background` registry slug that appears in the event slug pool to appear in `tracked_npcs_active[]`, plus any gold `expected_tracked_active_minimum` floor (`evals/stage_c_npc_candidates_vertical_slice/grader.py:358-412`, module doc `grader.py:20-25`). Stage D does not replace NC3; it **downstream-completes** cases Stage C leaves split across `unresolved_descriptors[]` and duplicate `new_npc_candidates[]`.

### Output contract (proposed; not implemented in repo)

A reasonable **StageDOutput** (or "extended Stage C") would add, at minimum:

- `resolved_entities[]` — each item: source pointer (e.g. "`unresolved_descriptors[2]`" or "`new_candidate slug pair`") → **resolution kind** (`merge_to_registry_slug` | `merge_to_canonical_new_candidate` | `new_net_entity`) → **canonical slug** (registry or proposed) → **evidence** (event indices, optional copy of supporting strings if allowed by policy).
- `proposed_aliases[]` — `{ target_slug, alias_text, source_descriptor_ids or evidence }` for GM/automation to add to `aliases[]` in `NpcRegistryRecord` (`src/contracts/npc_registry.py:29-42`).
- `proposed_new_records[]` — full or partial `NpcRegistryRecord`-shaped **candidate** rows for truly net-new people (status likely `candidate`, `hub_path: null` per convention) (`Docs/CONVENTION-Corpus-Subject-Schemas.md:180-188`).
- `unresolvable[]` — items that should stay ambiguous after resolution (legitimately generic descriptors, contradictory evidence, policy-withheld merges).

### Failure modes Stage D must cover that Stage C does not

- **Cross-bucket identity:** same person split between `unresolved_descriptors[]` and `new_npc_candidates[]`, or two `suggested_slug` variants for the same descriptor (`bubbles` vs `bubbles_the_float_goat` — see §2).
- **Registry / alias insufficiency:** user-facing phrasing in events ("the captain") not matching the model's first pass while `aliases[]` *could* cover it if extended (`step1_stage_c_run.py:149-156` already instructs alias matching; Stage D is where you **add** aliases after the fact).
- **`candidate` vs `tracked` semantics:** `NpcRegistryRecord` and NC3 today center on `tracked`/`background` in the grader's "positive list" (`grader.py:85-94`, `358-367`). Open product questions from the cross-campaign report (`Docs/Plans/REPORT-Stage-C-Cross-Campaign-Generalisation.md:125-129`) apply directly: when promotions happen and whether **recall** should include `candidate` rows.
- **PC negative-list re-validation** after transforming buckets (NC2 is strict on all three arrays — `grader.py:273-350`).
- **Slug hygiene:** enforce `^[a-z0-9_]+$` consistently (`grader.py:43-44`, `168-170`) after merges.

### Out of scope for Stage D (per architecture notes)

- **Authoring or rewriting NPC hub markdown** (dossier, timeline prose) — that is **Stage E** / GM workflow; CONVENTION §8 positions the registry as lookup for Stage C/D, not hub body authoring (`Docs/CONVENTION-Corpus-Subject-Schemas.md:180-188`).
- **Re-running Stage A** or changing `referenced_slugs[]` policy — tracked as separate Backlog work (`Backlog.md:60-67` for SE3/SE5 policy; `Backlog.md:36-40` for Stage A sidecar persistence).

---

## 2. Inventory of `unresolved_descriptors[]` patterns (S20 + C1 cohorts, 2026-04-22 sidecars)

**Method:** all 20 checked-in sidecars under `evals/stage_c_npc_candidates_vertical_slice/artifacts/runs/2026-04-22/` (5 runs × 4 scenarios) were aggregated with a small local parse (read-only). Note: the workspace file-search index may ignore `artifacts/` (e.g. gitignore), so file-indexed `grep` can miss these paths even when the files exist on disk.

### Counts (empirical)

| Scenario | Runs | `unresolved_descriptors` records (sum) | Per-run `unresolved_count` (telemetry) |
|----------|------|----------------------------------------|--------------------------------------|
| `stage_c_session1_c1` | 5 | **9** | `[2,2,2,1,2]` (avg **1.8**) |
| `stage_c_session2_c1` | 5 | **0** | all **0** |
| `stage_c_session3_c1` | 5 | **0** | all **0** |
| `stage_c_session20` | 5 | **0** | all **0** |

**Total:** 9 unresolved rows across 20 runs, **all from C1S1** only.

### Text patterns (actual descriptor strings, with multiplicity across the 9 rows)

- **2×** `a flaming, magma-infused spider monstrosity`
- **1×** each (variants of the same encounter): `mysterious cat owl`, `flaming, magma-infused spider monstrosity`, `cat owl`, `magma-infused spider monstrosity`, `a mysterious cat owl`, `a magma-infused spider monstrosity`, `the mysterious cat owl`

### Categorization

1. **Mergeable into existing tracked records**  
   *None* in this cohort's unresolved set — the unresolved rows are **not** mappable to Lysandra/Torbin (`captain_lysandra_ironveil` is absent from these C1S1 events in the "unresolved" rows; the issue set is **creature-description**, not "the captain" style).

2. **Mergeable into a `new_npc_candidates` row in the same run**  
   For C1S1, `new_npc_candidates` holds **Grishna** and **Glowkindle**; the unresolved lines are **not** names for those two — they are **separate encounter creatures**. A Stage D heuristic might still **cluster** the 8 variant strings about "cat owl" / "spider monstrosity" as **one display cluster** (slug-variant / description-variant deduplication) without asserting they equal Grishna or Glowkindle.

3. **Genuinely unresolvable (good candidates for `unresolvable[]` or "no registry row")**  
   The model's own rationales point here — e.g. *"The creature is described but not clearly named as an NPC, so its identity cannot be confidently resolved."* (`…run001.json`, `stage_c_output.unresolved_descriptors[0]`, lines 73-79 in the sampled sidecar). Same pattern for the "spider monstrosity" line (`…run001.json:81-86`).

4. **Slug-variant / aggregation duplicates (not in `unresolved_descriptors` but in `new_npc_candidates`)**  
   This is the **bubbles** case. Across **C1S3** five runs, aggregation gives: **`bubbles` ×1** and **`bubbles_the_float_goat` ×4**, same `descriptor: "Bubbles the Float Goat"` — matching the cross-campaign report and proposals file (`Docs/Plans/REPORT-Stage-C-Cross-Campaign-Generalisation.md:79-81`; `evals/stage_c_npc_candidates_vertical_slice/proposals/c1_registry_proposals_20260422T213552Z.json:78-100`).

**Note on the cross-campaign write-up:** The narrative bullet in the cross-campaign report mentions C1S2 in the same sentence as C1S1's unresolved average. **The committed 2026-04-22 sidecars show `unresolved_count: 0` for every C1S2 run** — treat the **on-disk artifacts** as ground truth for this audit; the report line may be imprecise or refer to a different revision.

**Kirfan / "elderly fisherman" (Stage D motivation vs this artifact set):** The C1S3 **fixture** includes `referenced_slugs: ["kirfan"]` while narrative text still says *"fisherman's net"* (`evals/stage_c_npc_candidates_vertical_slice/fixtures/stage_a_events_session3_c1.json:35-40`). In that world, Stage C **correctly** emits `new_npc_candidates` with `descriptor: "Kirfan"` (5/5) — the hard **Stage D** case is when Stage A **omits** `kirfan` from `referenced_slugs[]` (the Kirfan-class regression in `Backlog.md`), not what these gold fixtures show.

---

## 3. Heuristic vs LLM split

### Strong fit for **deterministic** post-processors (no extra model call)

| Sub-task | Rationale | Cost vs correctness |
|----------|-----------|----------------------|
| **PC negative-list re-check** | Same substring logic as NC2 (`grader.py:106-127`, `273-350`). Cheap, high precision for blocking unsafe merges. | **Low cost, high value**; risk is **over-blocking** (substring "stafl" in unrelated word — unlikely with roster terms). |
| **Slug normalization / variant clustering** for `suggested_slug` | Empirical `bubbles` / `bubbles_the_float_goat` split (§2). Levenshtein + containment + "same descriptor string" is standard. | **Low cost**; correctness high when descriptor identical; **false merges** if two different NPCs share a short nickname. |
| **Registry alias / display_name substring pass** for **unresolved** text vs existing rows | Implements what the Stage C prompt already asks the model to do once (`step1_stage_c_run.py:149-156`); the model still misses. | **High precision** when alias is a true substring; **low recall** for pronouns/roles ("the medic") with no string overlap. |
| **Event-slug pool sanity (registry_active ∪ `referenced_slugs` ∪ `participants`)** | NC3's pool construction is explicit (`grader.py:73-82`, `358-383`). A Stage D "did we account for every pool slug?" check mirrors NC3. | **Deterministic, low cost**; doesn't solve identity merging, but catches **dropped** slugs. |

### Likely need an **LLM** (or human) pass

| Sub-task | Rationale | Cost vs correctness |
|----------|-----------|----------------------|
| **Semantic coreference** ("the elderly fisherman" ⟺ Kirfan) when **no** shared substring and **no** `referenced_slugs[]` | Requires narrative / cross-field reasoning; the repo documents this as a **summary-vs-prose** failure mode (`Backlog.md`, Kirfan-class entry). | **High per-call cost** for marginal recall if overused; best scoped to **small** `unresolved` + recap snippets, not full corpus. |
| **Display_name / `first_session` / `last_session` inference** for new registry rows | `NpcRegistryRecord` requires multiple fields and session bounds (`src/contracts/npc_registry.py:29-42`). | Expensive to do safely unattended; good as **propose-only** output for GM edit. |
| **Choosing canonical slug** under ambiguity ("shortest" vs "full epithet" — Backlog slug-derivation entry) | Policy choice with tradeoffs, not a pure string edit. | Wrong automation **commits** a bad `slug` for years; **Stage D** should either propose options or follow a **fixed, documented** rule. |

**Backlog on calibration before autonomy:** The write-surface item explicitly says: measure Stage D accuracy on a labelled cohort; if **>~95%** on alias adds, `dry_run` → `confirm` is reasonable; if lower, **propose-only** is safer.

**Skeptical counterpoint:** A single LLM pass for "resolve everything" can **hallucinate** merges; the eval harness should keep **heuristic + optional LLM** (with golden fixtures) to separate **reliable string merge** from **semantic coreference**.

---

## 4. Write-surface design space

**Backlog** lays out **three** options: CLI, **autonomous with two-phase `corpus_writer` pattern**, and **propose-only sidecar** (Backlog "NPC registry — write surface for Stage D resolutions" entry).

| Pattern in repo | What it favors |
|-----------------|----------------|
| **`src/agent/corpus_writer.py`** | `dry_run` → `confirm_token` → commit; strict allowlist — today **does not** include `_npc_registry.json` (`src/agent/corpus_writer.py:1-20`, `183-197`; allowlist in `is_writable_corpus_path` `33-58`). A registry writer would be a **new** allowlist entry + new tool surface if following this path. |
| **`evals/.../proposals/c1_registry_proposals_*.json`** + cohort aggregation | **Propose-only, GM review**; zero mutation of canonical corpus; fits "measure error rate first" in the Backlog entry. |
| **`scripts/lint_npc_registry.py`** | **Read-only** today (`scripts/lint_npc_registry.py:1-18`); any writer or proposals sidecar must pass schema + hub existence rules; Backlog already notes **extending** lint for a proposals file if (iii) wins. |
| **`.cursor/rules/dispatch-guard-grader-separation.mdc`** | Runtime **guards** vs **eval graders** are separate; graders verify recovery, not duplicate policy (`dispatch-guard-grader-separation.mdc:7-24`). A **planner** tool that mutates the registry would need a **dispatch guard**; a **batch eval-only** Stage D writer to `artifacts/` does not. |

**Recommendation:** **Default to propose-only sidecars** (option iii) for **first vertical slice and early production** — it matches shipped cohort `proposals/` momentum, keeps **lint + GM review** as the safety gate, and avoids new allowlist / guard complexity before calibration. **Counter-argument:** **Alias-only** high-confidence updates might be fine via a small **CLI** (option i) long-term without touching the planner at all — the Backlog's own text treats alias adds as potentially lighter than full `candidate` row proposals.

---

## 5. Vertical slice sketch: `evals/stage_d_entity_resolution_vertical_slice/`

**Mirror of Stage C layout** (`evals/stage_c_npc_candidates_vertical_slice/README.md:15-36`):

- `step1_stage_d_run.py` — input: **frozen** `StageCOutput` JSON + `events` + `registry` + `pc_roster` + `campaign_id` (same loaders as `step1_stage_c_run.py:108-122`).
- `grader.py` — gates **ER1–ER5** (below).
- `gold/*.json` — expected merges / forbidden merges.
- `fixtures/` — **frozen** Stage C sidecars: e.g. copy from `artifacts/runs/2026-04-22/` (C1S1 with unresolved text; C1S3 with `bubbles` split; S20 with PC-leak path if you want a **negative** test that Stage D must not "merge" PCs).
- `artifacts/runs/YYYY-MM-DD/` — `stage_d--…json` with `StageDOutput` + grades.

### Gold examples (grounded in repo data)

1. **Slug-variant merge:** Input: C1S3 `new_npc_candidates` with `bubbles` and `bubbles_the_float_goat` (from §2) + registry row `bubbles_the_float_goat` with `aliases: ["Bubbles"]` (`corpus/.../Campaign 1/_npc_registry.json:25-32`). **Expected:** one canonical `bubbles_the_float_goat` decision; `proposed_aliases[]` may be empty or confirm `"Bubbles"`.
2. **Unresolvable creature descriptions:** Input: C1S1 `unresolved_descriptors` for "mysterious cat owl" / "spider monstrosity" variants (`…run001.json:73-86`). **Expected:** `unresolvable[]` (or `resolved_entities` with `kind: no_new_registry_row`) — **not** merged into `grishna` or `glowkindle` without new evidence.
3. **Alias attach to existing tracked (synthetic or future):** If registry has `aliases: ["the captain"]` for Lysandra and events only say "the captain" — **Expected:** `resolved_entities` → `captain_lysandra_ironveil` (this is a **designed** gold, not in the 2026-04-22 unresolved set, which is creature-heavy).

### Proposed grader gates

| Gate | Intent |
|------|--------|
| **ER1** | Output schema: required arrays, IDs, no orphan pointers; all slugs `^[a-z0-9_]+$` (inherit NC1's spirit — `grader.py:43-44`). |
| **ER2** | **PC safety:** no resolution may introduce PC terms into a registry-attach path that NC2 would forbid (mirror `grader.py:273-350`). |
| **ER3** | **No false merges (precision):** e.g. `bubbles` must not map to a different NPC than `Bubbles the Float Goat` cluster; "cat owl" must not merge to **Grishna** in gold. |
| **ER4** | **Recall / completeness (within scope):** e.g. all slug variants in input that gold marks as `must_merge` appear as one canonical decision. |
| **ER5** | **Registry / status policy:** e.g. if `candidate` records are in scope, resolutions must not violate `hub_path` rules (`Docs/CONVENTION-Corpus-Subject-Schemas.md:186-188` + `src/contracts/npc_registry.py:54-62`). |

**Minimum runner:** Python + Pydantic `StageDOutput` + one OpenAI `responses_parse` (if LLM) **or** pure Python (if v1 deterministic-only), reusing `DungeonMindApiClient` pattern from `step1_stage_c_run.py:291-301`.

---

## 6. Open risks and sequencing

### Top 3 risks

1. **Ambiguous `candidate` vs `tracked` in NC3 and Stage D** — product + grader policy still open (`Docs/Plans/REPORT-Stage-C-Cross-Campaign-Generalisation.md:125-129`; Backlog GM-review entry). Stage D that "resolves to registry" must know whether **`candidate` counts** as *known* for merge targets.

2. **`referenced_slugs[]` and Stage A policy** — until Stage A persistence + grader policy settle (Backlog Stage A sidecar persistence entry; SE3/SE5 policy entry), end-to-end **semantic** loss (Kirfan class) will confound **Stage D** quality metrics. Stage D can still ship on **heuristic** slices using frozen good fixtures.

3. **Over-merge / slug-collision** — aggressive substring or fuzzy slug merge can collapse **two** NPCs (short names, shared "captain" tokens). You need **precision** gates (ER3) and possibly **human** review of proposals.

### Should Stage D ship next?

**Case for shipping Stage D next:** Stage C is proven 19/20 with clear buckets; the repo already has a **one-record `candidate` promotion** (`bubbles_the_float_goat` in `corpus/.../Campaign 1/_npc_registry.json`) to test `candidate` semantics; a **propose-only** vertical slice is **low product risk** and unblocks a measured answer to the write-surface question.

**Case for other work first:**
- (a) **Stage A sidecar persistence** unblocks *many* runs without hand-frozen events — high leverage for all downstream evals.
- (b) **Slug-derivation** at Stage C overlaps with Stage D's variant merge — fixing upstream **reduces** duplicate `new_candidate` load but **does not replace** cross-run aggregation.
- (c) **GM promotion** of the remaining C1 proposals increases NC3 signal when those names appear in later sessions' events.

**Balanced call:** A **small Stage D vertical slice (deterministic + one gold for semantic optional)** is a good *parallel* track; the **highest system-wide leverage** is still **Stage A artifact persistence** if your bottleneck is *running* large cohorts. If the bottleneck is *registry + identity correctness*, **Stage D + propose-only** is the clean next step; **fully autonomous registry writes** should wait for calibration as Backlog already states.

---

## 7. TL;DR (one paragraph)

**Stage D** should consume frozen **`StageCOutput` + the same `events` / registry / PC roster** as Stage C, and produce **auditable** merge decisions (resolved entities, alias proposals, net-new `candidate` records, and a true **unresolvable** set), while **out of scope** for hub or timeline authoring. In the **shipped 2026-04-22** cohort, **`unresolved_descriptors[]` is entirely a C1S1 "creature not clearly named as an NPC" pattern** (8 related strings, 9 rows), while **the slug-variant** problem shows up in **C1S3 `new_npc_candidates` (`bubbles` vs `bubbles_the_float_goat`)**; **Kirfan is not an unresolved line in those fixtures** because `referenced_slugs[]` already carries `kirfan`. **Design effort** is front-loaded: **status/candidate** semantics, **write surface** (propose-only vs confirm), and **ER** gates; **implementation** can start **deterministic** (PC re-check, substring/alias, slug clustering) and add a **narrow** LLM for coreference. The **cleanest first step** is a **`evals/stage_d_entity_resolution_vertical_slice/`** with **frozen** Stage C sidecars from `…/artifacts/runs/2026-04-22/`, **ER1–ER5** grading, and **propose-only JSON** as the only output surface until you have labelled accuracy to justify touching `_npc_registry.json` via CLI or `corpus_writer.py`.

---

*Audit constraints: read-only; all counts from the 20 on-disk `stage_c--*.json` sidecars; line citations refer to the repo at audit time. Artifacts may be gitignored for workspace `grep` — use direct file paths or a script if reproducing.*
