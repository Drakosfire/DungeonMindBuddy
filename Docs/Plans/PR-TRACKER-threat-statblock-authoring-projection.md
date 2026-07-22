# PR Tracker — Threat + Statblock Authoring and Projection

**Status:** ACTIVE SLICE / REVIEW AUTHORITY  
**Date:** 2026-07-22  
**Design:** [`../Design/DESIGN-threat-statblock-authoring-projection-workflow.md`](../Design/DESIGN-threat-statblock-authoring-projection-workflow.md)  
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)  
**Contract owner:** DungeonMindServer owns statblock mechanics, validation, persistence, revisions, and provider assets. DungeonBuddy owns drafts, orchestration, graph identity/bindings, projections, documents, combat runtime, and media selection.

This tracker is the implementation sequencing authority for this workstream. It does not override Campaign Supergraph sequencing for unrelated graph infrastructure.

## 1. Slice conventions

- Stable design IDs are `SBW01` through `SBW18`.
- Only `SBW01` currently carries a tentative future PR number in its filename. Assign actual GitHub PR numbers when dispatching against a known merged base.
- Every handoff after `SBW01` is **pre-designed**, not automatically ready. Re-anchor its base SHA, paths, generated contracts, fixtures, commands, and stop conditions at dispatch.
- One PR establishes one independently useful capability and one invariant.
- Cross-layer work is allowed only when every changed layer establishes or proves that same invariant.
- No PR may silently add graph writes, mechanics persistence, document persistence, media selection, combat mutation, or autonomous confirmation when its mission excludes them.
- Any new durable schema is versioned and proved by exact round-trip/reload tests.
- Exact IDs and revisions are authoritative. Display labels, corpus paths, artifact names, and “latest” never silently substitute.
- Replacement paths are deleted when the replacement becomes production-ready unless the PR names the exact remaining consumer and deletion owner.

Required demolition block in every implementation handback:

```text
Replaced path:
Deleted in this PR: yes | no
If no, retained reason:
Named remaining consumer:
Required deletion owner:
```

## 2. Sequence summary

| Slice | Status | Depends on | One outcome |
|---|---|---|---|
| `SBW01` | READY | Server v1 merged | One server-owned Buddy→DungeonMind client/readiness boundary. |
| `SBW02` | BLOCKED | `SBW01` conventions | Versioned durable non-canonical ThreatDraft CRUD. |
| `SBW03` | BLOCKED | `SBW01–02` | One exact draft version generates one traceable candidate. |
| `SBW04` | BLOCKED | `SBW03` | Shared renderer + real read-only candidate workbench. |
| `SBW05` | BLOCKED | `SBW04` | Complete typed editing + exact-digest preview validation. |
| `SBW06` | BLOCKED | `SBW05` | New candidate from exact source with lineage/status. |
| `SBW07` | BLOCKED | `SBW05`; `SBW06` optional | Idempotent immutable first mechanics revision. |
| `SBW08` | PARALLEL READY after graph stabilization | Current graph contracts | Typed external-resource and Threat binding graph contract. |
| `SBW09` | BLOCKED | `SBW07–08` + graph confirm | Governed Threat + exact binding publication. |
| `SBW10` | BLOCKED | `SBW09` | Exact-revision Threat Sheet projection. |
| `SBW11` | READY after document re-anchor | Current document/writer contracts | Fresh Plan open hydrates committed content safely. |
| `SBW12` | BLOCKED | `SBW10–11` | Exact revision-pinned Markdown/Tiptap block. |
| `SBW13` | BLOCKED | `SBW06–07`, `SBW10` | Append immutable child revision + compare; no migration. |
| `SBW14` | BLOCKED | `SBW13` + graph replacement semantics | Adopt child for one exact Threat binding only. |
| `SBW15` | BLOCKED | `SBW10` | Exact-revision combat seed/insertion/reload/drilldown. |
| `SBW16` | BLOCKED | `SBW04` | Explicit optional candidate image generation. |
| `SBW17` | BLOCKED | `SBW10`, `SBW16` | Durable image selection for exact target/role. |
| `SBW18` | DEFERRED | `SBW17` dogfood + operator choice | 3D use-case/provider/contract reconnaissance. |

## 3. Slice contracts

### SBW01 — Server-owned DungeonMind statblock v1 client and readiness

**Handoff:** [`HANDOFF-pr382-statblock-v1-backend-client-readiness.md`](HANDOFF-pr382-statblock-v1-backend-client-readiness.md)  
**Status:** READY FOR DISPATCH.

**Mission:** establish one server-owned authenticated client/readiness/error boundary for all later DungeonMind statblock operations.

**Invariant:** no browser, route, or feature service constructs privileged DungeonMind HTTP calls directly.

**Acceptance:** honest configured/available capabilities; bounded timeout; auth/rate-limit/not-found/conflict/schema errors remain distinct; exact read fixture retains IDs/digest; credentials never leave server/log-safe boundary.

**Non-goals:** drafts, generation workflow, UI, persistence, graph, documents, combat, media.

**Demolition:** none; foundational boundary.

---

### SBW02 — Versioned ThreatDraft store and CRUD API

**Handoff:** [`HANDOFF-sbw02-threat-draft-store.md`](HANDOFF-sbw02-threat-draft-store.md)  
**Status:** pre-designed; blocked on `SBW01` route/config conventions.

**Mission:** persist and revise a non-canonical threat concept independently of downstream providers.

**Invariant:** successful authored updates preserve `draft_id` and increment version exactly once.

**Acceptance:** strict `ThreatDraftV1`; atomic create/read/list/update; stale 409 writes nothing; restart reload exact; graph context stores pointers only; no Server/graph/corpus calls.

**Demolition:** retain legacy `StatblockDraftArtifactView` until `SBW04` replaces its user-facing consumer.

---

### SBW03 — Generate candidate from one exact ThreatDraft version

**Handoff:** [`HANDOFF-sbw03-generate-candidate-from-draft.md`](HANDOFF-sbw03-generate-candidate-from-draft.md)  
**Status:** blocked on `SBW01–02`.

**Mission:** generate and reload one typed candidate from one exact draft version.

**Invariant:** every outcome is bound to draft ID/version/request ID; authored fields remain unchanged.

**Acceptance:** deterministic request mapping; images default false; stale version blocks before downstream; typed success/failure; reloadable candidate ref/cache with non-authoritative status; replay/partial failure truthful.

**Demolition:** none yet; mock UI remains until `SBW04`.

---

### SBW04 — Shared semantic renderer and real candidate workbench

**Handoff:** [`HANDOFF-sbw04-semantic-renderer-candidate-workbench.md`](HANDOFF-sbw04-semantic-renderer-candidate-workbench.md)  
**Status:** blocked on `SBW03`.

**Mission:** make a real typed candidate reviewable through one renderer reusable by later projections.

**Invariant:** structured definition and receipts are the only mechanics sources.

**Acceptance:** fixture matrix covers simple, spellcasting, legendary/lair, phased, and human-adjudicated definitions; missing/expired/unavailable states retain identity; shared token/accessibility rules; normal mock/corpus-first presentation removed.

**Demolition:** remove mock generation/render and corpus promotion/retrieval controls from the normal workbench. Retain backend predecessors only for named consumers.

---

### SBW05 — Complete-definition edit and preview validation

**Handoff:** [`HANDOFF-sbw05-typed-candidate-edit-validation.md`](HANDOFF-sbw05-typed-candidate-edit-validation.md)  
**Status:** blocked on `SBW04`.

**Mission:** edit a complete typed working definition and validate the exact digest through DungeonMindServer.

**Invariant:** validation applies only to the submitted complete-definition digest; any edit invalidates it.

**Acceptance:** no sparse patches/schema fork; complex unknown structures preserved; errors/warnings distinct; issue paths map or remain global; failure retains edits; persistence is honestly session-only unless separately designed.

**Demolition:** remove any UI claiming Markdown-only edits change mechanics.

---

### SBW06 — Candidate revise/regenerate and lineage

**Handoff:** [`HANDOFF-sbw06-candidate-revise-lineage.md`](HANDOFF-sbw06-candidate-revise-lineage.md)  
**Status:** blocked on `SBW05`.

**Mission:** create a new candidate from one exact edited definition, candidate, or accepted revision while preserving source lineage.

**Invariant:** revision creates a new candidate ID; source proposals/revisions are never overwritten.

**Acceptance:** exact source/no latest; explicit instructions digest; active/superseded/rejected/accepted-source transitions; failure retains source/editor; replay and downstream-success/local-write recovery safe.

**Demolition:** remove any regenerate action that replaces current output without lineage.

---

### SBW07 — Persist accepted mechanics as immutable first revision

**Handoff:** [`HANDOFF-sbw07-persist-accepted-mechanics.md`](HANDOFF-sbw07-persist-accepted-mechanics.md)  
**Status:** blocked on `SBW05`; `SBW06` optional for first save.

**Mission:** idempotently persist one validation-clean definition and record its exact immutable locator on the draft.

**Invariant:** mechanics saved means exact `(statblock_id, revision_id, definition_digest)` and never implies graph publication.

**Acceptance:** stale/error validation blocks; double-submit creates once; exact reload proves IDs/digest; post-commit local failure is recoverable; UI says saved/not published.

**Demolition:** corpus promotion is not an acceptance path and is deleted from the normal workflow when no named consumer remains.

---

### SBW08 — World Graph external resource and binding contract

**Handoff:** [`HANDOFF-sbw08-world-graph-statblock-binding-contract.md`](HANDOFF-sbw08-world-graph-statblock-binding-contract.md)  
**Status:** parallel-ready after current graph contract changes stabilize.

**Mission:** store, validate, fingerprint, reload, traverse, and project a typed Threat→external-statblock binding.

**Invariant:** graph state contains external identity and binding metadata only; selected revision/digest participate in semantic identity; mechanics never enter graph.

**Acceptance:** strict node/edge state; endpoint/provider/ID agreement; immutable publish/reload/projection; same binding replay idempotent; changed revision distinct; definition-shaped payload rejected.

**Stop trigger:** generic graph-property architecture or ontology change is required.

---

### SBW09 — Governed Threat + exact binding publication

**Handoff:** [`HANDOFF-sbw09-governed-threat-binding-publication.md`](HANDOFF-sbw09-governed-threat-binding-publication.md)  
**Status:** blocked on `SBW07–08` and current graph confirm path.

**Mission:** prepare, review, confirm, and verify a planned Threat plus exact mechanics binding.

**Invariant:** only reviewed revision-bound graph effects commit; saved mechanics remain valid when publication fails.

**Acceptance:** explicit existing/new identity; planned/GM/campaign defaults; no-write preview; proposal/token/parent-bound confirm; stale/replay safe; partial state recoverable; exact committed revision proves node/resource/binding.

**Demolition:** no direct graph-file or statblock-specific writer may exist.

---

### SBW10 — Exact-revision Threat Sheet

**Handoff:** [`HANDOFF-sbw10-exact-revision-threat-sheet.md`](HANDOFF-sbw10-exact-revision-threat-sheet.md)  
**Status:** blocked on `SBW09`.

**Mission:** open a graph Threat as one composed identity + exact mechanics projection.

**Invariant:** every displayed mechanic matches the exact selected binding IDs/digest; no latest/name/corpus/cache substitution.

**Acceptance:** deterministic binding selection or explicit ambiguity; two Threats can share mechanics with distinct lore; Server unavailable preserves identity/locator; shared renderer; exact graph revision stability.

**Demolition:** replace named artifact/corpus statblock-view consumers with exact revision identity.

---

### SBW11 — Committed Plan-document hydration

**Handoff:** [`HANDOFF-sbw11-plan-document-content-hydration.md`](HANDOFF-sbw11-plan-document-content-hydration.md)  
**Status:** can dispatch after current document/writer re-anchor.

**Mission:** reopen a registered Plan document from committed Markdown after a fresh browser/session state.

**Invariant:** exact registered committed content hydrates deterministically; compatible dirty local work is never overwritten; missing committed content never masquerades as starter/saved data.

**Acceptance:** safe read by document ID only; save→fresh reload; dirty-local revision/fingerprint precedence; stale conflict; missing/unsupported diagnostics; existing writer unchanged.

**Non-goal:** statblock block itself.

---

### SBW12 — Revision-pinned Markdown/Tiptap embed

**Handoff:** [`HANDOFF-sbw12-revision-pinned-markdown-tiptap-embed.md`](HANDOFF-sbw12-revision-pinned-markdown-tiptap-embed.md)  
**Status:** blocked on `SBW10–11`.

**Mission:** store and render an exact statblock locator as a typed Plan document block across commit/fresh reload.

**Invariant:** provider/statblock/revision/view/threat attributes round-trip semantically and never select latest or copy canonical mechanics.

**Acceptance:** strict directive grammar; Tiptap node/commands; invalid attrs make zero backend calls; exact shared projection; missing/unavailable retains locator; mixed document and fresh reload pass.

**Demolition:** remove live embeds that copy pending Markdown as mechanics source when replaced.

---

### SBW13 — Append immutable revision and compare

**Handoff:** [`HANDOFF-sbw13-append-revision-compare.md`](HANDOFF-sbw13-append-revision-compare.md)  
**Status:** blocked on `SBW06–07`, `SBW10`.

**Mission:** fork an exact parent, append one immutable child, and compare typed mechanics.

**Invariant:** child has one exact expected parent; parent remains readable; no use migrates.

**Acceptance:** stale parent/no latest; idempotent append/recovery; semantic diff covers rule elements, phases, spellcasting, rules/adjudicated text; bindings/embeds/placements/combat unchanged.

**Demolition:** remove in-place save semantics for accepted revisions.

---

### SBW14 — Governed one-binding revision adoption

**Handoff:** [`HANDOFF-sbw14-governed-binding-revision-upgrade.md`](HANDOFF-sbw14-governed-binding-revision-upgrade.md)  
**Status:** blocked on `SBW13` and graph replacement/supersession semantics.

**Mission:** replace one exact Threat binding’s selected revision through governed review.

**Invariant:** exactly one binding changes; every sibling binding, embed, placement, and combatant remains unchanged.

**Acceptance:** exact current/new IDs/digests/same logical statblock; one no-write replacement preview; stale/replay safe; exact graph verification; multiple-active binding integrity check; sibling non-mutation ledger.

**Non-goal:** bulk, preferred/latest, document/combat migration.

---

### SBW15 — Exact-revision combat adapter

**Handoff:** [`HANDOFF-sbw15-exact-revision-combat-adapter.md`](HANDOFF-sbw15-exact-revision-combat-adapter.md)  
**Status:** blocked on `SBW10`.

**Mission:** derive deterministic `CombatantSeedV1` and insert mutable exact-revision combatants into the existing tracker.

**Invariant:** exact locator/snapshot remain immutable while HP/init/conditions/notes mutate only combat state.

**Acceptance:** typed seed; exact derivation/no corpus fallback; network replay safety; save/load/export locator+snapshot; offline row operation; exact drilldown; no active auto-upgrade.

**Demolition:** replace legacy artifact/corpus combat-add identity when no named consumer remains.

---

### SBW16 — Optional candidate image generation

**Handoff:** [`HANDOFF-sbw16-optional-image-generation.md`](HANDOFF-sbw16-optional-image-generation.md)  
**Status:** blocked on `SBW04`; parallel thereafter.

**Mission:** explicitly request optional images during supported candidate generate/revise operations and display typed asset outcomes.

**Invariant:** image outcome is non-blocking presentation work; mechanics validity/digest remain independent; only typed durable `AssetRefV1` is trusted.

**Acceptance:** default false; real readiness/Server contract; partial image failure retains candidate mechanics; safe MIME/URL rendering; candidate reload assets; no selection/upload/delete/3D.

**Cross-repo stop:** if image-only regeneration requires a new Server route, dispatch a separate DungeonMindServer PR first.

---

### SBW17 — Durable image selection and binding

**Handoff:** [`HANDOFF-sbw17-durable-image-selection-binding.md`](HANDOFF-sbw17-durable-image-selection-binding.md)  
**Status:** blocked on `SBW10`, `SBW16`.

**Mission:** persist one trusted provider asset for one exact Threat/binding presentation role and compose it into existing views.

**Invariant:** exact provider asset + target + role change presentation state only; mechanics, graph identity, and provider ownership remain unchanged.

**Acceptance:** trusted server-side asset resolution; strict target/role matrix; optimistic replace/unbind; candidate expiry survives; deterministic slot precedence; CDN failure honest; binding-level media never silently transfers; digest unchanged.

**Demolition:** remove transient/data-URI/provider URL usage as durable selected media where replaced.

---

### SBW18 — 3D media contract reconnaissance

**Handoff:** [`HANDOFF-sbw18-3d-media-contract-reconnaissance.md`](HANDOFF-sbw18-3d-media-contract-reconnaissance.md)  
**Status:** DEFERRED / NOT READY.

**Mission:** select one concrete 3D use case/provider and define a distinct model/job/storage contract with evidence and split successor handoffs.

**Invariant:** 3D is a typed media resource with canonical file, preview, variants, provenance, job state, ownership, and delivery requirements—not an image URL with a different extension.

**Acceptance:** operator-selected use case/provider; official evidence; licensing/retention/ownership decision; format/MIME/CDN/range proof; identity/job/persistence matrices; separate Server and Buddy implementation handoffs; documentation/fixtures only.

**Stop:** no selected use case/provider, no durable download, unresolved licensing, unstable identity/idempotency, insecure delivery, or cross-repo implementation coupling.

## 4. Critical review gates

Before dispatching any slice:

1. Fetch current `main` and record immutable base SHA.
2. Read the complete canonical handoff; do not dispatch a chat summary.
3. Verify all predecessor PRs named by the handoff are merged.
4. Re-anchor expected paths and generated type/fixture names.
5. Confirm no stop condition is already true.
6. Update the handoff only through a reviewed docs change when repository drift changes the contract materially.
7. Assign the actual GitHub PR number/branch after the base is known.
8. Require the implementation handback to distinguish author-local, independently rerun, CI, and manual evidence.

## 5. Cumulative proof record

After `SBW15` and `SBW17`, add one report under `Docs/Reports/` proving the real Shepherds' Flock/Mireward flow:

```text
World Graph/Hermes context
→ ThreatDraft
→ typed candidate
→ edit/validate/revise
→ immutable mechanics
→ governed Threat binding
→ exact Threat Sheet
→ committed Plan embed fresh reload
→ child revision compare and optional one-binding adoption
→ combat runtime
→ image generation + selection
```

The report records IDs, revisions, receipts, failure injections, screenshots/recordings where appropriate, and demolition outcomes. It does not replace the owning-boundary tests or authorize `SBW18`.
