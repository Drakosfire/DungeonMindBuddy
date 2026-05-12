# Convention: Session recap breadcrumbs and session memory

**Status:** Prescriptive for derivative recap indexes under `Longmont Campaign/Campaign N/Session Recaps/`.
**Upstream:** [`Docs/CONVENTION-Session-Recap-Normalization.md`](CONVENTION-Session-Recap-Normalization.md) (`_normalized/` prepared recaps).
**Path resolver:** `src/corpus/session_recap_paths.py`.

---

## 1. Purpose

Breadcrumb markdown and compiled session-memory JSONL are **derivative retrieval indexes** over prepared normalized recap prose. They live in the corpus beside the session stack so planners, harnesses, and operators share one durable layout instead of experiment-only paths under `evals/`.

---

## 2. Directory layout

Under `Longmont Campaign/Campaign N/Session Recaps/`:

| Directory | Contents |
|-----------|----------|
| (root) | Original play recaps (`document_class: play`) |
| `_normalized/` | Prepared narrative-only recaps (`dmb_recap_normalized_v1`) |
| `_breadcrumbed/` | Inline-tagged breadcrumb artifacts (`dmb_recap_breadcrumbs_v1`) and optional `*.frontmatter_seed.md` staging |
| `_session_memory/` | Committed `*.records_meta.jsonl` + companion `*.records_meta.json` |

World-layer setting hubs under `Elderwyld/` are unchanged; session stacks are campaign-layer only.

---

## 3. Filename contract

Use the **same basename** as the sibling `_normalized/` file (see [`Docs/INDEX-Recap-Normalization.md`](INDEX-Recap-Normalization.md)):

- `_breadcrumbed/{basename}.breadcrumbed.md`
- `_breadcrumbed/{basename}.frontmatter_seed.md` (optional)
- `_session_memory/{basename}.records_meta.jsonl`
- `_session_memory/{basename}.records_meta.json`

---

## 4. Breadcrumb artifact

- Schema: `dmb_recap_breadcrumbs_v1`.
- `source_recap_path` MUST be the corpus-relative `_normalized/…` path for new and migrated work.
- Inline tags follow `evals/sentence_routing_retrieval_falsification/breadcrumb_smoke.py` `ALLOWED_TAG_TYPES`.
- Tag-stripped body MUST match the normalized recap body (whitespace contract in `breadcrumb_normalize.py`).
- Prep-only spans omitted from `_normalized/` are out of scope for the breadcrumb index unless indexed elsewhere.

**Promotion:** LLM or experiment outputs under `evals/sentence_routing_retrieval_falsification/manual_labels/artifacts/` are staging. Blessed copies land under corpus `_breadcrumbed/`.

---

## 5. Session memory

- Build: `uv run python scripts/materialize_session_memory.py` (wraps `normalize_breadcrumb_artifact` + `write_records_jsonl`).
- JSONL rows use schema `dmb_session_memory_record_v1`.
- Companion JSON summarizes `source_recap_path`, `campaign_id`, `session_number`, `unit_count`, `records_with_routes`, etc.
- Session memory is **rebuildable** from the breadcrumb file; committed copies support deterministic cohort `--check` lanes.

---

## 6. Corpus writes

Create paths via `write_corpus_file` (`src/agent/corpus_writer.py`) allowlist:

- `**/Session Recaps/_breadcrumbed/Session … - ….breadcrumbed.md`
- `**/Session Recaps/_breadcrumbed/Session … - ….frontmatter_seed.md`
- `**/Session Recaps/_session_memory/Session … - ….records_meta.jsonl`
- `**/Session Recaps/_session_memory/Session … - ….records_meta.json`

---

## 7. Eval harness boundary

Gold scenarios, cohort manifests, frozen baselines, and run reports remain under `evals/sentence_routing_retrieval_falsification/`. They reference corpus `_session_memory/` JSONL paths; they do not host canonical breadcrumb bodies.
