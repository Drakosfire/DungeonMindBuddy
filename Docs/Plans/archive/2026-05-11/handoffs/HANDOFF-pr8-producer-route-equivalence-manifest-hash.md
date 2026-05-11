---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description. Dispatcher fills once; reviewers and parallel
# agents see one stable shape without inferring sections from free-form §2 prose.
pr_body_template: |
  ## Summary

  Bump route-equivalence **producer** JSONL to **`schema_version` `0.3.0`** with deterministic **`route_equivalence_manifest_hash`** plus **`producer_registry_path`** (workspace-relative POSIX) and **`producer_registry_sha256`** on every `RouteEquivalenceRecord` line; regenerate committed `route_equivalence_longmont_c*_v1.jsonl`; extend loader + lexicon tests. **Does not** touch `breadcrumb_query_run.py`, `cohort_baseline_run.py`, gold, or corpus content beyond reading registry bytes for hashing.

  ## Verification (verbatim §7)

  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat origin/main...HEAD` (§4 paths only)

  ```text
  {{TODO}}
  ```

  ## What stayed unchanged

  {{TODO: one paragraph — `evals/.../breadcrumb_query_run.py` untouched; `cohort_baseline_run.py` untouched; `route_equivalence_shadow.py` untouched except if TypeScript/JSON consumers are unaffected; gold untouched; no retrieval flip; shadow diagnostic shape at the harness boundary unchanged in *semantics* (edge counts); wider cohort + canvas `--skip-*` derivation explicitly a different slice.}}
---

> **MERGED** 2026-05-11 — merge commit `adeb060911be35f4f477cb15eaf701ab7d409fbf` — [PR #8](https://github.com/Drakosfire/DungeonMindBuddy/pull/8). Pre-merge head `91fb12ee1b09e03b6653148124e5a2f8816dbcdc`; review `4260634217` (APPROVE intent via COMMENTED self-review). Atomic doc-sync completed in PLAN **v15** + CHECKLIST + this archive move.

# HANDOFF — PR #8: Producer `manifest_hash` + registry provenance on route-equivalence JSONL

**Created:** 2026-05-11 (UTC).
**Status:** MERGED — post-merge doc-sync complete; this file lives under `Docs/Plans/archive/2026-05-11/handoffs/`.
**Parent agent:** Cursor agent; dispatcher performed the post-merge **atomic** doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc` and `.cursor/rules/anchor.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` **v15** (`active_phase: B`, **M2 in_progress**, **M3 in_progress**). This handoff was the **PR #8** slice: **producer-side** `manifest_hash` + provenance on `route_equivalence_longmont_c*_v1.jsonl` at **`schema_version` `0.3.0`**.

**Explicit fork (read before scope creep):** The CHECKLIST **next slice** is an **OR**: this PR **OR** a wider cohort (records + manifest for `c1s13_v1` / `natural_v1`). **This handoff is only the producer JSONL lane.** The **hardcoded `--skip-c1s*-canvas-refresh`** triplet in `cohort_baseline_run.run_one_scenario` (**PR #7 rubric carry-forward**) is **required before widening the cohort manifest** but is **OUT OF SCOPE for PR #8** — ship it as a tiny follow-up PR or fold it into the **wider-cohort** handoff, not here. Mixing producer-schema work with cohort-runner argv reflow in one PR creates dual-review-surface risk.

---

## §1 Mission

Ship **deterministic provenance + a self-consistent manifest hash** on every line of the committed Phase B route-equivalence artifacts `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl` and `route_equivalence_longmont_c2_v1.jsonl` by extending `RouteEquivalenceRecord` (`schema_version` **`0.3.0`**), teaching `build_route_equivalence_manifest` / `write_route_equivalence_manifest` to populate the new fields, bumping `route_equivalence_loader.py` supported schema versions, **regenerating** both JSONL files under `--write`, and proving **`--check`** byte-stability + full lexicon pytest green — **without** editing harness, cohort runner, shadow builder, or gold.

## §2 Why this slice (context for the subagent)

- **PR #3** committed the JSONL artifacts; **PR #6**/**PR #7** built cohort baselines and L2 recall **assuming** those artifacts are the canonical producer output. Today each line carries **`schema_version` `0.2.0`** and edge semantics only — there is **no** cryptographic tie from an edge row back to the **`_npc_registry.json`** bytes that produced it, and no **file-level** self-consistency hash for drift detection beyond raw byte compare.
- **PR #7** `github-pr-7.rubric_when_we_judge` explicitly calls out that **L2 on the tight cohort is all `null`** — the PLAN's re-sequencing decision prioritizes **producer provenance (this slice)** and/or **wider cohort** before **L3** true A/B. This slice closes the **producer provenance** branch so future “who changed the artifact?” forensics and cross-service `manifest_hash` patterns (see `evals/corpus_remote/*` for prior art on `manifest_hash`) have a first-class home on the **producer** JSONL rows.
- **What this slice does NOT do:** no `breadcrumb_query_run.py`, no `cohort_baseline_run.py`, no `route_equivalence_shadow.py` behavioral changes unless TypeScript/JSON strict consumers break on unknown keys (they should not — JSONL is row-schemaless to consumers using pydantic); no **retrieval** / **ranking** / **`session_memory_query.py`**; no gold edits; no **wider cohort** records or manifests; no **canvas `--skip-*` argv** fix (denylisted). No change to **`shadow_route_equivalences`** schema id (`dmb_route_equivalence_shadow_v1`) — shadow payload shape stays as today; new fields ride **inside** loaded records only if something JSON-serializes full records (today shadow does not dump per-edge JSON into the cohort summary).

## §3 Authoritative inputs (read these before writing code)

| Path | Why |
|---|---|
| `src/lexicon_phase_b/schemas.py` | `RouteEquivalenceRecord` — today `extra="forbid"`, `schema_version` default **`0.2.0`**. This PR bumps contract. |
| `src/lexicon_phase_b/route_equivalence_manifest.py` | `build_route_equivalence_manifest`, `write_route_equivalence_manifest`, canonical **`sorted(records, key=lambda r: r.record_id)`** writer ordering. |
| `src/lexicon_phase_b/route_equivalence_loader.py` | `SUPPORTED_ROUTE_EQUIVALENCE_SCHEMA_VERSIONS` gate — must admit **`0.3.0`** after bump; decide whether **`0.2.0`** remains loadable for external stale files (recommend **drop 0.2.0 from committed artifacts only**, keep loader strict for **0.3.0** once committed files regenerate — document choice in PR body). |
| `scripts/build_route_equivalence_manifests.py` | Default registry paths + `--write` / `--check` UX — likely unchanged API; must still exit **0** on `--check` after regen. |
| `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py` | Byte-identity contract vs committed JSONL — **must** update golden bytes after regen. |
| `tests/lexicon_phase_b/test_route_equivalence_record_defaults.py` | Pins default `schema_version` — update to **`0.3.0`** and new required fields if defaults exist. |
| `tests/lexicon_phase_b/test_route_equivalence_loader.py` | Loader happy-path + error strings — extend for **`0.3.0`** rows. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl` | Real line shape today — read **one** line for field inventory before editing schema. |
| `Docs/Plans/archive/2026-05-10/handoffs/HANDOFF-route-equivalence-shadow-source-paths-workspace-relative.md` | Historical note: producer `manifest_hash` was explicitly deferred from PR #5 — this PR is that deferred slice. |

## §4 Allowlist — only these paths may be touched

| Path | Action | Purpose |
|---|---|---|
| `src/lexicon_phase_b/schemas.py` | modify | Add **`0.3.0`** fields to `RouteEquivalenceRecord`; bump default `schema_version` to **`0.3.0`**; keep **`extra="forbid"`**. |
| `src/lexicon_phase_b/route_equivalence_manifest.py` | modify | Compute **`producer_registry_sha256`** once per registry build; compute **`producer_registry_path`** as **workspace-relative POSIX** from repo root; compute **`route_equivalence_manifest_hash`** per §6.2; attach to each emitted record; preserve deterministic sort. |
| `src/lexicon_phase_b/route_equivalence_loader.py` | modify | Admit **`0.3.0`** in `SUPPORTED_ROUTE_EQUIVALENCE_SCHEMA_VERSIONS`; tighten error messages if needed. |
| `scripts/build_route_equivalence_manifests.py` | modify | Only if required to plumb repo-root for relative path helper — **minimize**; prefer keeping logic in `route_equivalence_manifest.py`. |
| `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py` | modify | Regenerate expectations: byte-identity vs committed JSONL; pin **`schema_version`** assertion to **`0.3.0`**; add **one** test that **`route_equivalence_manifest_hash`** is **identical on every non-blank line** in each committed file. |
| `tests/lexicon_phase_b/test_route_equivalence_record_defaults.py` | modify | Align defaults / constructor pins with **`0.3.0`**. |
| `tests/lexicon_phase_b/test_route_equivalence_loader.py` | modify | Load committed **`0.3.0`** artifacts; negative test for unsupported schema if retained. |
| `tests/lexicon_phase_b/test_route_equivalence_manifest.py` | modify | Add **one** focused test proving §6.2 preimage sensitivity (semantic field change ⇒ hash changes). |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl` | modify | Regenerated bytes (**`--write`** then commit verbatim). |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl` | modify | Regenerated bytes (**`--write`** then commit verbatim). |

**Expected diff stat shape:** **10** paths. If `git diff --stat` shows anything else, **revert** — scope creep.

## §5 Denylist — do not touch (revert if seen in diff)

| Path | Why |
|---|---|
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Harness lane — unrelated; reviewer will **REQUEST_CHANGES**. |
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Cohort runner — **canvas `--skip-*` fix belongs to wider-cohort / follow-up PR**, not PR #8. |
| `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` | Consumer diagnostic builder — PR #8 is producer-only; shadow already loads records via loader; **no edits** unless CI proves a **runtime** crash after loader change (then **stop** and ask parent — still try to fix in loader/schema first). |
| `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Harness-boundary suite — must stay green **without modification** (§7 proves this). |
| `tests/test_cohort_baseline_run.py` | Cohort baseline tests — must stay green **without modification** (§7 proves this). |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | Cohort frozen baseline — **must not reroll** in this PR unless a **deterministic** harness failure proves byte drift from JSONL semantic equivalence (unexpected — denylist by default; investigate first). |
| `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` | Cohort manifest — wider cohort is a **different** handoff. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold never edited for producer provenance. |
| `corpus/**` | Do not “fix” registry content — read-only `read_bytes()` for SHA-256. |
| `src/agent/session_memory_query.py` | Phase C **exit** / L3 — forbidden. |
| `src/prompts/**` | Forbidden. |
| `Docs/Plans/**` | Doc-sync is **parent post-merge**, not worker. |

## §6 Implementation contract

### 6.1 New `RouteEquivalenceRecord` fields (`schema_version` **`0.3.0`**)

All **required** (not optional) — every JSONL line must validate under pydantic after load:

| Field | Type | Constraints |
|---|---|---|
| `schema_version` | `str` | **Literal** or pinned string **`"0.3.0"`** on every new row (no mixed versions in one file). |
| `producer_registry_path` | `str` | **Workspace-relative POSIX** path to the **`_npc_registry.json`** file used as input for **this** campaign's build (same string on every line within one output file). Use the same normalization approach as PR #5's harness: `path.resolve().relative_to(repo_root.resolve()).as_posix()` with a **`ValueError` → defensive fallback** documented in code comment if registry ever lives outside repo (should not for default registries). |
| `producer_registry_sha256` | `str` | **Lowercase hex SHA-256** of **`Path(producer_registry_path).resolve().read_bytes()`** at build time — **same value on every line** within one output file. |
| `route_equivalence_manifest_hash` | `str` | **Lowercase hex SHA-256** of the **manifest preimage** (§6.2) — **same value on every line** within one output file. |

**Naming:** PLAN prose says `manifest_hash`; row field **`route_equivalence_manifest_hash`** avoids collision with unrelated `manifest_hash` keys in other subsystems and stays grep-friendly.

### 6.2 Manifest preimage (normative — implement exactly)

1. Let `records_sorted = sorted(records, key=lambda r: r.record_id)` after **`producer_registry_path`** and **`producer_registry_sha256`** are populated on every record, and **before** `route_equivalence_manifest_hash` exists.
2. For each record `r` in `records_sorted` (in that order), build `payload = r.model_dump(mode="json", exclude={"route_equivalence_manifest_hash"})`, then `line = json.dumps(payload, sort_keys=True, ensure_ascii=False)`.
3. **Preimage string:** `preimage = "\n".join(lines)` where `lines` is the list from step 2 in **`records_sorted` order**.
4. **`route_equivalence_manifest_hash`** `= hashlib.sha256(preimage.encode("utf-8")).hexdigest()` (lowercase hex).
5. **Assign** the same hash string to **every** record via `model_copy(update={"route_equivalence_manifest_hash": <hash>, "schema_version": "0.3.0"})` (or equivalent), then call **`write_route_equivalence_manifest`** which emits **sorted by `record_id`** as today; each line is the full `model_dump(mode="json")` **including** `route_equivalence_manifest_hash`.

### 6.3 Registry root resolution

`repo_root = Path(__file__).resolve().parents[2]` inside `src/lexicon_phase_b/route_equivalence_manifest.py` reaches the **DungeonMindBuddy repo root** (validate with one `assert (repo_root / "pyproject.toml").is_file()` in a unit test or inline comment). **`producer_registry_path`** is always relative to this root for default builds.

### 6.4 Loader

- Add **`"0.3.0"`** to `SUPPORTED_ROUTE_EQUIVALENCE_SCHEMA_VERSIONS`.
- **Policy:** After this PR lands, **committed** JSONL under `evals/.../artifacts/lexicon/` are **only** `0.3.0`. If keeping **`0.2.0`** support for out-of-tree files, document it; otherwise **remove `0.2.0`** from the frozenset and update tests to match.

### 6.5 Regenerate + prove byte stability

```bash
uv run python scripts/build_route_equivalence_manifests.py --write
uv run python scripts/build_route_equivalence_manifests.py --check   # must exit 0
```

Committed files must match generator output **byte-for-byte**.

## §7 Verification commands (run all; paste output verbatim into PR description)

> **Numbering note:** each non-comment line inside the single ```bash``` fence is **exactly one** shell invocation (no blank lines inside `python -c` strings). Parser count must be **11** to pair with §8 / §9.

```bash
# 1. Producer lane unit + integration tests (entire lexicon package).
uv run pytest tests/lexicon_phase_b/ -q

# 2. Byte-stable artifact regression.
uv run pytest tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py -q

# 3. Loader-focused tests.
uv run pytest tests/lexicon_phase_b/test_route_equivalence_loader.py -q

# 4. Manifest builder + preimage sensitivity test (must gain the §6.2-focused test).
uv run pytest tests/lexicon_phase_b/test_route_equivalence_manifest.py -q

# 5. Record defaults contract.
uv run pytest tests/lexicon_phase_b/test_route_equivalence_record_defaults.py -q

# 6. Producer CLI determinism gate.
uv run python scripts/build_route_equivalence_manifests.py --check

# 7. Harness-boundary suite — must pass with ZERO edits to this file in PR #8.
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q

# 8. Cohort baseline suite — must pass with ZERO edits to this file in PR #8.
uv run pytest tests/test_cohort_baseline_run.py -q

# 9. Frozen cohort summary `--check` — must exit 0.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check

# 10. One manifest hash per file (c1 + c2); schema_version 0.3.0 on first line of each file.
uv run python -c "import json;from pathlib import Path;[print(p.name,'manifest_hashes',len({json.loads(l)['route_equivalence_manifest_hash'] for l in p.read_text(encoding='utf-8').splitlines() if l.strip()}),'schema',next(json.loads(l)['schema_version'] for l in p.read_text(encoding='utf-8').splitlines() if l.strip())) for p in (Path('evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl'),Path('evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl'))]"

# 11. One registry sha256 per file + print workspace-relative producer_registry_path from first c1 line.
uv run python -c "import json;from pathlib import Path;p=Path('evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl');lines=[l for l in p.read_text(encoding='utf-8').splitlines() if l.strip()];o=json.loads(lines[0]);regs=set(json.loads(l)['producer_registry_sha256'] for l in lines);print('c1_registry_sha256_distinct',len(regs),'producer_registry_path',o.get('producer_registry_path'))"
```

## §8 Reporting contract

1. **§7:** paste stdout/stderr tails for all **11** commands; §7 **#10** must print **`manifest_hashes` `1`** for each file and **`schema` `0.3.0`**; §7 **#11** must print **`c1_registry_sha256_distinct` `1`** and a **`producer_registry_path`** with no absolute prefix.
2. **`git diff --stat origin/main...HEAD`** filtered to **§4 paths only** — expect **10** rows (one per allowlisted path).

## §9 Acceptance rubric (each bullet pairs with §7; reviewer uses `fetch --extract-rubric`)

- [ ] **`RouteEquivalenceRecord.schema_version` is `0.3.0` on every committed JSONL line** — verified by §7 **#10** (`schema` column) plus §7 **#1** green (and loader §7 **#3**).
- [ ] **`producer_registry_path` is workspace-relative POSIX** (no drive letters, no absolute `/home/...` prefixes) for default registries — verified by §7 **#11** `producer_registry_path` token + reviewer spot-check.
- [ ] **`producer_registry_sha256` is lowercase hex length 64** and **constant across all lines in each file** — verified by §7 **#11** (`c1_registry_sha256_distinct` `1`) plus focused assertions in §7 **#2** / **#4** as applicable.
- [ ] **`route_equivalence_manifest_hash` is lowercase hex length 64** and **constant across all lines in each file** — verified by §7 **#10** (`manifest_hashes` `1` per file) plus §7 **#2** line-constant test.
- [ ] **Manifest preimage matches §6.2 normative definition** — verified by **one** new focused test in **`tests/lexicon_phase_b/test_route_equivalence_manifest.py`** (§7 #4) that mutates a semantic edge field and asserts **`route_equivalence_manifest_hash`** changes while holding registry meta constant.
- [ ] **`write_route_equivalence_manifest` preserves `sorted(records, key=lambda r: r.record_id)` emission order** — verified by existing determinism tests + §7 #2.
- [ ] **`scripts/build_route_equivalence_manifests.py --check` exits 0** after regen — §7 **#6**.
- [ ] **Committed JSONL bytes match fresh `--write` output byte-for-byte** — same discipline as PR #3; §7 **#6** implies this.
- [ ] **Loader accepts committed artifacts** — §7 **#3**; rejects stale **`0.2.0`** if policy says drop (negative test optional).
- [ ] **Harness + cohort regression bundles unchanged** — §7 **#7** breadcrumb harness green (paste `N passed` line), §7 **#8** cohort pytest green (paste `N passed` line), §7 **#9** `cohort_baseline_run --check` exit **0** — **without** editing those test files or harnesses.
- [ ] **No §5 denylist paths appear in `git diff`** — reviewer will **REQUEST_CHANGES** if violated.
- [ ] **Cost:** `$0` — no LLM calls; producer CLI + pytest only.

## §10 Naming + post-merge parent duties

- **Handoff / PR title suggestion:** `PR #8: producer route-equivalence manifest hash + registry provenance (JSONL 0.3.0)`.
- **Post-merge (parent, one atomic batch):** DONE — `PLAN.version` **15**; `external_pull_requests.github-pr-8` with **≥3 new** `rubric_when_we_judge` bullets; **CHECKLIST** Phase B + Reanchor + session log; L3 not started.
- **Archive:** this file moved to `Docs/Plans/archive/2026-05-11/handoffs/` with completion banner (same pattern as PR #6/#7).

---

**End of handoff.** Dispatcher: run `uv run python scripts/review_external_pr.py fetch 8 --handoff Docs/Plans/HANDOFF-pr8-producer-route-equivalence-manifest-hash.md --extract-rubric` **after** the PR opens to confirm §4/§5/§7/§9 parse; fix table headers if parser reports `denylist: 0`.
