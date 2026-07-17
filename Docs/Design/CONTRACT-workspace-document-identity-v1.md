# Contract — Workspace Document Identity v1

**Status:** ACTIVE  
**Date:** 2026-07-16  
**Scope:** Authored workspace documents for `/plan` boards and Tiptap runbooks  
**Out of scope:** Ingestion/evidence `document_id` values (`doc_*`), graph node IDs, agent thread IDs

---

## 1. Decision

Authored workspace documents use **opaque, server-issued UUIDs** as identity. Human-facing meaning lives in typed metadata fields. Document IDs are never parsed for campaign, session, kind, or title.

Ingestion/evidence `doc_*` identifiers remain a **separate provenance namespace**. They identify chunked corpus sources in retrieval indexes and must not be reused as workspace document IDs.

---

## 2. Record shape

Registry schema: `dmb_workspace_document_registry_v1`  
Record schema: `dmb_workspace_document_record_v1`  
Persistence: `out/registries/workspace_documents.json`

| Field | Owns |
| --- | --- |
| `document_id` | Opaque UUID. Equality-only. Never displayed as the document name. |
| `title` | Editable human label. May collide. |
| `campaign_id` | Campaign scope. Explicit field, not an ID substring. |
| `target_session` | Optional numeric “prep for Session N” metadata. |
| `kind` | `plan` or `runbook`. |
| `target_relpath` | Optional durable Markdown publish path. Registry-owned. |
| `status` | Lifecycle: `active` or `discarded`. Discard retains the record. |
| `content_status` | `draft` or `committed` (relative to durable Markdown write). |
| `revision` | Monotonic CAS token for metadata/write races. |
| `created_at` / `updated_at` | ISO-Z timestamps. |

Hard delete is not part of this contract. Discard sets `status=discarded` and keeps the row for restore/audit.

---

## 3. API surface

Prefix: `/api/live`

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/workspace-documents` | List (default `status=active`) |
| `POST` | `/workspace-documents` | Create (server issues UUID) |
| `GET` | `/workspace-documents/{document_id}` | Read |
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

- Local draft storage key: `dmb.workspaceDocument.{documentId}` with schema `dmb_workspace_document_local_state_v2`.
- Agent thread index/active keys include `documentId` when a document is selected.
- URL selection uses `?documentId=<uuid>`. `?session=` remains memory/graph focus only.
- Do not derive identity from title, `prepSession`, or path basename at runtime.
- Opening without `documentId` resolves or creates an active plan document via the registry.

---

## 5. Boundary from ingestion evidence IDs

| Namespace | Example | Purpose |
| --- | --- | --- |
| Workspace documents | `11111111-1111-4111-8111-111111111111` | Plan/runbook authoring artifacts |
| Evidence documents | `doc_city_of_mirathorn` | Chunked corpus provenance for retrieval |

Never join these namespaces by string rewriting. If a future feature needs a link, store an explicit foreign key field.

---

## 6. Seed / cutover

`scripts/seed_workspace_documents.py` creates registry rows for:

- Longmont `Session N Prep.md` files that match the Markdown writer allowlist
- The two Tiptap spike runbook Markdown targets under `evals/c2_live_prep/.../tiptap/`

Other Session Prep filenames are reported as ambiguous and require manual resolution. Old browser-local semantic keys are not dual-read after cutover.
