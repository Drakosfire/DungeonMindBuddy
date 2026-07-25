# Contract — Workspace Document Identity v1

**Status:** ACTIVE  
**Date:** 2026-07-16  
**Updated:** 2026-07-22 (BLD-02 worldbuilding_source)  
**Scope:** Authored workspace documents for `/plan` boards, Tiptap runbooks, and Build worldbuilding sources  
**Out of scope:** Ingestion/evidence `document_id` values (`doc_*`), graph node IDs, agent thread IDs, SourceArtifact IDs

---

## 1. Decision

Authored workspace documents use **opaque, server-issued UUIDs** as identity. Human-facing meaning lives in typed metadata fields. Document IDs are never parsed for campaign, session, kind, or title.

Ingestion/evidence `doc_*` identifiers remain a **separate provenance namespace**. They identify chunked corpus sources in retrieval indexes and must not be reused as workspace document IDs.

Workspace document IDs are also a **separate namespace from SourceArtifact IDs**. BLD-03 may link a committed workspace revision to an immutable SourceArtifact via explicit foreign keys (`workspace_document_id`, `workspace_document_revision`, `content_sha256`); it must never rewrite a workspace UUID into a source-artifact ID.

---

## 2. Record shape

Registry schema: `dmb_workspace_document_registry_v1`  
Record schema: `dmb_workspace_document_record_v1`  
Persistence: `out/registries/workspace_documents.json`

| Field | Owns |
| --- | --- |
| `document_id` | Opaque UUID. Equality-only. Never displayed as the document name. |
| `title` | Editable human label. May collide. |
| `campaign_id` | Campaign or world scope. Explicit field, not an ID substring. |
| `target_session` | Optional numeric “prep for Session N” metadata. Optional for worldbuilding sources. |
| `kind` | `plan`, `runbook`, or `worldbuilding_source`. |
| `target_relpath` | Optional durable Markdown publish path. Registry-owned. |
| `status` | Lifecycle: `active` or `discarded`. Discard retains the record. |
| `content_status` | `draft` or `committed` (relative to durable Markdown write). |
| `revision` | Monotonic CAS token for metadata/write races. |
| `created_at` / `updated_at` | ISO-Z timestamps. |
| `source_domain` | Required `worldbuilding` for `worldbuilding_source`; null otherwise. |
| `document_class` | Required non-empty class label for worldbuilding sources (e.g. `lore`, `faction`). |
| `authority_state` | `draft` / `reviewed` / `canonical` for worldbuilding sources; null otherwise. |
| `visibility_state` | `internal` / `player_safe` for worldbuilding sources; null otherwise. |

Hard delete is not part of this contract. Discard sets `status=discarded` and keeps the row for restore/audit.

### Worldbuilding target policy

For `kind=worldbuilding_source`:

- Clients **must not** supply `target_relpath` on create or update.
- The registry assigns `out/workspace/worldbuilding/{document_id}.md`.
- The Markdown writer accepts only that exact registry-owned path.
- Unsupported Markdown constructs (tables, HTML, images, thematic breaks) are commit-blocking; prepare returns `writer_ok=false` and commit rejects without mutation.

Plan and runbook targets retain their existing allowlists.

---

## 3. API surface

Prefix: `/api/live`

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/workspace-documents` | List (default `status=active`) |
| `POST` | `/workspace-documents` | Create (server issues UUID) |
| `GET` | `/workspace-documents/{document_id}` | Read metadata record |
| `GET` | `/workspace-documents/{document_id}/snapshot` | Coherent record + Markdown + content fingerprint (BLD-05a) |
| `PATCH` | `/workspace-documents/{document_id}` | Metadata update (optional `expected_revision`) |
| `POST` | `/workspace-documents/{document_id}/discard` | Retained discard |
| `POST` | `/workspace-documents/{document_id}/restore` | Restore to active |

Markdown writer:

| Method | Path | Body |
| --- | --- | --- |
| `POST` | `/tiptap/markdown-write/prepare` | `{ document_id, markdown, expected_revision? }` |
| `POST` | `/tiptap/markdown-write/commit` | `{ document_id, markdown, writer_confirm_token, expected_revision? }` |

The writer resolves `title` and `target_relpath` from the registry. Clients must not supply them. Discarded documents and documents without `target_relpath` cannot be written. Confirm tokens bind `document_id + registry_revision + relpath + content + file_state`.

---

## 4. Client rules

- Local draft storage key: `dmb.workspaceDocument.{documentId}` with schema `dmb_workspace_document_local_state_v3` (includes `base_revision` + `base_content_sha256`; supports `worldbuilding_source` / `build`).
- Agent thread index/active keys include `documentId` when a document is selected.
- URL selection uses `?documentId=<uuid>`. `?session=` remains memory/graph focus only.
- Worldbuilding / Build agent scope uses `sessionNumber: null` (never synthetic `0`).
- Do not derive identity from title, `prepSession`, or path basename at runtime.
- Opening Build without `documentId` is an explicit new-source state (no durable write until create).
- Plan may still resolve/create an active plan document via the registry when no `documentId` is present.
- Warning-level Markdown import diagnostics are commit-blocking for durable writes.
- Snapshot integrity: `content_status=committed` with missing/unreadable target bytes is a fail-closed error, not an empty editor.

---

## 5. Boundary from ingestion evidence IDs

| Namespace | Example | Purpose |
| --- | --- | --- |
| Workspace documents | `11111111-1111-4111-8111-111111111111` | Plan/runbook/worldbuilding authoring artifacts |
| Evidence documents | `doc_city_of_mirathorn` | Chunked corpus provenance for retrieval |
| Source artifacts (BLD-03+) | distinct immutable IDs | Graph evidence lineage; linked by foreign keys only |

Never join these namespaces by string rewriting. If a future feature needs a link, store an explicit foreign key field.

---

## 6. Seed / cutover

`scripts/seed_workspace_documents.py` creates registry rows for:

- Longmont `Session N Prep.md` files that match the Markdown writer allowlist
- The two Tiptap spike runbook Markdown targets under `evals/c2_live_prep/.../tiptap/`

Other Session Prep filenames are reported as ambiguous and require manual resolution. Old browser-local semantic keys are not dual-read after cutover. Worldbuilding sources are created through the registry API, not the seed script, unless a later slice adds explicit seeds.
