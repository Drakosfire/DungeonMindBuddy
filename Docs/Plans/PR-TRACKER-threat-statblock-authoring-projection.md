# PR Tracker — Threat + Statblock Authoring and Projection

**Status:** ACTIVE SLICE / REVIEW AUTHORITY
**Date:** 2026-07-21
**Design:** [`../Design/DESIGN-threat-statblock-authoring-projection-workflow.md`](../Design/DESIGN-threat-statblock-authoring-projection-workflow.md)
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)
**Contract owner:** DungeonMindServer statblock v1; DungeonBuddy consumes generated contracts and owns workflow/projection/graph/runtime.

This tracker is the implementation sequencing authority for this workstream. It does not override Campaign Supergraph sequencing for unrelated graph infrastructure.

## 1. Slice conventions

- Stable slice IDs are `SBW01` etc.; future GitHub PR numbers are assigned only when dispatching.
- One PR establishes one independently useful capability.
- A PR may touch backend, UI, and tests only when all paths prove one invariant.
- No PR may silently add graph writes, mechanics persistence, media generation, or combat mutation when its mission excludes them.
- Any new durable schema must be versioned and fixture-tested.
- Replacement paths are deleted in the same PR that makes the replacement production-ready unless a named consumer blocks deletion.

Required demolition block in every PR:

```text
Replaced path:
Deleted in this PR: yes | no
If no, retained reason:
Named remaining consumer:
Required deletion owner:
```

## 2. SBW01 — Server-owned DungeonMind statblock v1 client and readiness

**Status:** READY

**Mission:** Establish one DungeonBuddy backend adapter that can authenticate to DungeonMindServer statblock v1, read health/readiness, and perform typed request/response/error translation without exposing credentials or adding product workflow.

**Invariant:** Every later statblock operation crosses one server-owned typed client boundary; no UI or service constructs privileged DungeonMind HTTP requests directly.

**Repository:** DungeonMindBuddy only.

**Depends on:** Merged DungeonMindServer statblock v1 route and the existing generated-client/fingerprint proof.

**Deliverables:**

- Server-side configuration for base URL, internal key, enabled flag, and timeout.
- A narrowly scoped client/adapter with methods matching v1 operations, initially proving health/readiness and exact revision read or fixture-backed transport.
- Stable typed error categories: unavailable, authentication/configuration, timeout, rate limit, invalid request/validation, not found, conflict, downstream unexpected.
- A DungeonBuddy readiness projection that reports configured/available capabilities honestly.
- Unit tests with a fake transport; no real credentials or network dependency.

**Expected paths:**

- new integration module under `apps/live_control_server/services/` or a bounded new `integrations/` package;
- `apps/live_control_server/routes/live.py` only if a narrow readiness endpoint is needed;
- `apps/live-control-ui/src/api/types.ts` / `liveApi.ts` only if readiness is surfaced now;
- focused Python tests.

**Non-goals:** ThreatDrafts, candidate generation, UI workbench changes, graph writes, persistence, Markdown, combat, images, Server changes.

**Acceptance:**

- Missing config produces deterministic unavailable readiness.
- Invalid key maps distinctly from downstream validation.
- Timeout is bounded and typed.
- Exact response parsing uses generated/contract-derived DTOs or fixture-locked server models, not permissive dictionaries.
- Tests prove internal key never appears in a response or log assertion.

**Demolition:** None; establishes a new boundary.

**Stop conditions:** The generated contract cannot be consumed server-side without introducing a handwritten canonical schema; the Server readiness contract is insufficient to distinguish enabled capabilities; authentication requires a browser token.

**Named successor:** `SBW02` and `SBW03`.

## 3. SBW02 — Versioned ThreatDraft store and CRUD API

**Status:** BLOCKED on SBW01 route/config conventions only; domain design ready.

**Mission:** Add a durable, non-canonical, versioned `ThreatDraftV1` that can be created, edited, listed, read, and reloaded with no generation or graph side effects.

**Invariant:** Authored threat prose has stable identity and survives independently of provider calls, candidates, accepted mechanics, and graph publication.

**Repository:** DungeonMindBuddy only.

**Deliverables:**

- Strict `ThreatDraftV1` and nested intent/context/pointer models.
- File-backed or existing service-store-aligned repository with atomic writes and bounded IDs.
- Create/list/read/update endpoints.
- Optimistic version check on update; stale update fails 409.
- Graph context snapshot accepts only revision/node/source-anchor pointers already produced by existing graph/Plan paths.
- UI-independent tests for reload and version conflict.

**Non-goals:** Generate, validate, candidate cache, accept, graph write, renderer, media.

**Acceptance:** Draft survives restart/reload; version increments; invalid campaign/world/focus/pointer shapes fail closed; update never changes `draft_id`; no graph head or DungeonMind call occurs.

**Demolition:** Do not delete transitional `StatblockDraftArtifactView` yet; normal UI still consumes it until SBW04.

**Stop conditions:** Existing generic artifact store cannot enforce version/reload semantics without broad migration; draft storage would require using corpus Markdown as the record.

**Named successor:** `SBW03`.

## 4. SBW03 — Generate candidate from one exact ThreatDraft version

**Status:** BLOCKED on SBW01+SBW02.

**Mission:** Map one exact ThreatDraft version into `GenerateCandidateRequestV1`, call DungeonMindServer, retain typed candidate metadata, and leave the draft intact on every failure.

**Invariant:** One generation result is traceable to one immutable draft version and request ID; provider outcome never mutates authored concept or graph truth.

**Repository:** DungeonMindBuddy only unless a discovered Server contract defect is reported separately.

**Deliverables:**

- Backend generate endpoint keyed by `draft_id` + expected draft version.
- Deterministic request mapping for ruleset, source snapshot, intent, encounter context, and `generate_images=false` default.
- Candidate reference/status appended to the draft through an atomic draft update.
- Bounded candidate-response cache or read-through locator sufficient for reload; cache explicitly non-authoritative.
- Typed failure envelope preserving retryability and request ID.
- API tests with fake DungeonMind adapter.

**Non-goals:** Renderer, mechanical editing, validation UI, accept, graph, images.

**Acceptance:** stale draft version rejects before downstream call; success records candidate reference; timeout/refusal/validation/provider failure preserves the draft; exact retry semantics are declared and tested; no candidate is labeled accepted.

**Demolition:** None yet; mock workbench remains until SBW04 presents the replacement.

**Stop conditions:** Candidate expiry makes reload impossible without a server candidate-read route; request mapping requires hidden corpus discovery rather than explicit pointers.

**Named successor:** `SBW04`.

## 5. SBW04 — Shared semantic statblock renderer and read-only candidate workbench

**Status:** BLOCKED on SBW03.

**Mission:** Render a real typed candidate in the existing Statblock Workbench through one reusable semantic renderer and replace the normal mock/corpus-first generation presentation.

**Invariant:** Candidate review, later full view, Markdown embed, and combat drilldown share one structured-definition rendering kernel.

**Repository:** DungeonMindBuddy only.

**Deliverables:**

- Shared statblock renderer components for identity, defense/vitality/movement, abilities/proficiencies, senses/communication, traits/actions/reactions/legendary/lair/phases, flavor, validation, and `human_adjudicated` display.
- Read-only candidate workbench loaded from a ThreatDraft candidate reference.
- Honest candidate/draft/validation/provenance status.
- Empty/unavailable/expired/error states retaining stable pointers.
- Component fixture coverage across simple, spellcasting, legendary/lair, phased, and human-adjudicated examples.

**Non-goals:** Editor, validation calls, accept, graph, combat, Markdown node, images.

**Acceptance:** renderer consumes generated contract types; candidate reload renders identically; no canonical Markdown parse; unsupported mechanics remain visible; route works from Plan's existing statblock tool projection.

**Demolition:** Remove mock generate/render from the normal workbench and remove corpus promotion/retrieval activation from the normal candidate path. Retain backend predecessors only if tests or a named legacy route still consume them; name deletion owner.

**Stop conditions:** Existing CSS/layout requires a separate renderer per host; renderer must reinterpret or regenerate accepted `rules_text`; fixture reveals a contract shape the generated client cannot represent.

**Named successor:** `SBW05`, `SBW14`.

## 6. SBW05 — Complete-definition candidate editing and preview validation

**Status:** BLOCKED on SBW04.

**Mission:** Let the GM edit a complete typed candidate working copy and validate it through DungeonMindServer without persisting mechanics.

**Invariant:** Every mechanical edit remains a complete `StatblockDefinitionV1_Input` and receives authoritative Server validation before it can be accepted.

**Deliverables:**

- Editor state initialized from candidate definition.
- Explicit controls for first-release supported fields; safe structured fallback editor only if still contract-typed.
- Validate endpoint through the Buddy backend.
- Field-path issue mapping and global issue rail.
- Dirty/validated digest state; any edit invalidates prior validation.
- Reloadable editor draft or explicitly documented session-only state; do not imply persistence if absent.

**Non-goals:** Model revision, immutable save, graph, media, combat.

**Acceptance:** editing typed fields changes the submitted definition; validation errors block the future accept action; warnings remain visible; `rules_text` edits trigger revalidation; no untyped patch bag or local schema fork.

**Demolition:** Remove any remaining UI that edits only Markdown while claiming mechanics changed.

**Stop conditions:** A required field cannot be edited without creating a second handwritten schema; validation paths cannot map to fields; the UI must silently discard unknown rule elements.

**Named successor:** `SBW06`, `SBW07`.

## 7. SBW06 — Candidate revise/regenerate and lineage

**Status:** BLOCKED on SBW05.

**Mission:** Create a new typed candidate from an edited definition or exact revision plus explicit revision instructions, preserving candidate and draft lineage.

**Invariant:** Regeneration creates a new proposal; it never overwrites a draft version, accepted revision, or prior candidate silently.

**Deliverables:** revise endpoint; instruction model; source definition vs exact revision locator rules; preserve-element-key option; candidate lineage in draft review state; supersede/reject actions; typed downstream failures.

**Non-goals:** Persistence, graph, compare accepted revisions, media generation.

**Acceptance:** new candidate has a new ID; exact source is disclosed; prior candidate remains inspectable/statused; stale draft or source locator fails closed; provider failure leaves editor/draft intact.

**Demolition:** Remove any “regenerate” action that reuses mock output or replaces current state without lineage.

**Stop conditions:** Server revise semantics cannot preserve exact source provenance; candidate cache cannot distinguish superseded/rejected/expired.

**Named successor:** `SBW12`; also enriches SBW07 acceptance choices.

## 8. SBW07 — Persist accepted mechanics as immutable revision

**Status:** BLOCKED on SBW05; SBW06 optional for first save.

**Mission:** Save one validated complete definition into DungeonMindServer as a logical statblock + immutable first revision and record the exact accepted mechanics reference on the ThreatDraft.

**Invariant:** “Saved mechanics” always means an exact persisted `(statblock_id, revision_id, digest)`; it does not imply graph publication.

**Deliverables:** acceptance request/confirmation UI; stable idempotency key; create-statblock backend operation; persisted `AcceptedMechanicsRefV1`; `mechanics_saved` state; exact revision reload/proof; retry and conflict behavior.

**Non-goals:** Threat node, binding graph write, preferred campaign revision, Markdown, combat, image selection.

**Acceptance:** double-submit replays safely; validation errors cannot save; Server success survives Buddy response retry; reload resolves exact revision and digest; UI says mechanics saved/not published.

**Demolition:** Corpus write is no longer an acceptance path and should be deleted from the normal workbench if not already removed in SBW04.

**Stop conditions:** Idempotency cannot be stably derived/persisted; accepted reference cannot be written atomically to draft state; exact revision read disagrees with create response.

**Named successor:** `SBW09`, `SBW10`.

## 9. SBW08 — World Graph external statblock resource and binding contract

**Status:** READY in parallel after current graph-contract changes settle.

**Mission:** Extend Kernel/contribution/projection contracts to represent an external DungeonMind statblock resource node and typed `ThreatStatblockBinding` edge state, without publishing a product Threat.

**Invariant:** The graph can traverse Threat ↔ statblock relationships while canonical mechanics remain external and exact revision metadata remains typed and inspectable.

**Repository:** DungeonMindBuddy only.

**Deliverables:** strict external-resource/binding state models; materialization from `GraphContributionAssertion.value`; validation; projection/node-view/relationship-view exposure; semantic assertion identity/fingerprint behavior; fixtures/tests; no copied definition.

**Non-goals:** Workbench, Server calls, product graph proposal, ThreatDraft, persistence, preferred-revision UI.

**Acceptance:** resource node validates; binding edge validates only when provider/statblock/revision IDs match; state survives immutable graph publish/reload/projection; same binding reapply is idempotent; changed selected revision is semantically distinct; no statblock definition stored.

**Demolition:** None.

**Stop conditions:** arbitrary edge state cannot be introduced without a general graph property-contract decision; graph semantic identity would ignore selected revision and collapse distinct bindings; external-resource nodes violate an active ontology contract.

**Named successor:** `SBW09`.

## 10. SBW09 — Governed Threat + exact statblock binding publication

**Status:** BLOCKED on SBW07+SBW08 and available Graph Review confirm path.

**Mission:** Prepare, review, confirm, and reload a planned Threat plus exact statblock binding through the existing governed World Graph write path.

**Invariant:** A generated/saved statblock becomes campaign memory only through a revision-bound human-reviewed graph proposal and atomic Kernel publication.

**Deliverables:** map ThreatDraft + AcceptedMechanicsRef into authored source/contribution proposal; existing-object resolution; Threat node + external resource + binding edge review items; required metadata; preview UI; proposal-bound confirmation; pending publication recovery; exact committed revision verification.

**Non-goals:** Full Threat Sheet styling, Markdown, combat, revision upgrade, autonomous Hermes commit.

**Acceptance:** no confirm with zero/unreviewed effects; stale graph parent rejects; exact retry is idempotent; existing Threat can bind without duplicate node; new Threat defaults planned/GM/campaign-scoped; Server-saved mechanics remain usable if graph publish fails; reload proves node/edge at receipt revision.

**Demolition:** No direct graph-file or statblock-specific bypass writer may remain. Reuse normal graph authoring/Kernel path.

**Stop conditions:** current graph authoring prepare/commit cannot carry typed edge state; existing-object resolution cannot distinguish a new Threat from an existing one; graph write would require changing statblock mechanics.

**Named successor:** `SBW10`.

## 11. SBW10 — Exact-revision Threat Sheet and full statblock view

**Status:** BLOCKED on SBW09.

**Mission:** Open a graph Threat and compose its identity, exact selected statblock revision, binding, and media into one reusable Threat Sheet/full view.

**Invariant:** Every displayed mechanical field is traceable to the exact revision named by the binding or placement; the Threat remains a distinct world object.

**Deliverables:** resolver from graph binding to backend exact revision read; composed view model; summary/full views using shared renderer; graph/Plan open action; loading/missing/denied/downstream unavailable states; exact locator details behind opt-in diagnostics.

**Non-goals:** Edit accepted revision, Markdown node, combat mutation, images generation.

**Acceptance:** graph reload opens the same revision; same statblock may render for two Threats with distinct lore; no display-name lookup; unavailable Server preserves Threat identity and locator; latest revision does not silently replace selected revision.

**Demolition:** Remove generated-statblock view paths that identify canonical content by corpus artifact ID when the new exact-revision path replaces their named consumer.

**Stop conditions:** projection resolver cannot access binding state; UI requires direct browser call to Server; shared renderer cannot accept an exact revision definition.

**Named successor:** `SBW11`, `SBW12`, `SBW13`.

## 12. SBW11 — Revision-pinned Markdown/Tiptap statblock embed

**Status:** BLOCKED on SBW10.

**Mission:** Add a Tiptap/Markdown statblock node that stores an exact DungeonMind revision locator and renders the shared projection inside the Plan board.

**Invariant:** The document stores a stable typed locator; rendered mechanics are resolved projections, not copied canonical Markdown.

**Deliverables:** Markdown syntax/parser/serializer; Tiptap node; exact revision resolver; summary/full mode; unresolved state; insert action from Threat Sheet/workbench; reload and save tests; portable export explicitly separate if included.

**Non-goals:** Automatic latest upgrade, graph write, generic arbitrary React embed framework, combat.

**Acceptance:** save/reload preserves attributes byte-semantically; exact revision renders; missing revision remains editable and retains locator; newer revision does not change embed; document writer's existing prepare/commit safety remains intact.

**Demolition:** Remove any statblock embed/path that copies pending Markdown as the live source when its consumer is replaced.

**Stop conditions:** Markdown parser cannot round-trip directive attributes; Tiptap schema change would corrupt existing documents; resolver bypasses backend/auth boundary.

**Named successor:** `SBW12`.

## 13. SBW12 — Append revision, compare, and explicit upgrade

**Status:** BLOCKED on SBW10+SBW06.

**Mission:** Fork an accepted exact revision into an editable/revisable candidate, append an immutable child revision, compare it, and explicitly update chosen bindings/placements/embeds.

**Invariant:** New mechanics create a new revision; existing pinned uses remain unchanged until a scoped human action upgrades them.

**Deliverables:** open-as-candidate; append request with exact parent; stale-parent conflict; semantic compare view; campaign preferred selection if implemented; per-binding/per-placement/per-embed upgrade actions; audit/reload proof.

**Non-goals:** Bulk silent migration, automatic latest, combatant upgrade during active combat, merging divergent revision branches.

**Acceptance:** append creates new ID/digest; old revision remains readable; one embed/placement upgrade does not alter another; stale parent fails; compare includes rule elements and human-adjudicated text; no silent rebase.

**Demolition:** Remove in-place edit/save semantics for accepted revisions.

**Stop conditions:** binding replacement cannot be governed without a new graph proposal type; compare cannot preserve element identity; active combat state would be rewritten.

**Named successor:** later revision-branch/variant UX if dogfood demands it.

## 14. SBW13 — Exact-revision combat adapter

**Status:** BLOCKED on SBW10.

**Mission:** Derive a deterministic CombatantSeed from one exact statblock revision and insert it into the existing combat tracker with stable reload/export and full-view drilldown.

**Invariant:** Combat state is mutable encounter state pinned to immutable mechanics; no runtime mutation writes back to the statblock or graph.

**Deliverables:** expanded combat-minimum adapter; `CombatantSeedV1`; tracker insertion endpoint/action; exact locator + operational snapshot in persistence/export; drilldown through SBW10 resolver; human-adjudicated notices.

**Non-goals:** Full Play migration, rules automation, combat revision upgrade, graph write, encounter builder redesign.

**Acceptance:** add one or several instances; current/max HP behavior correct; reload/export retains locator and snapshot; revision unavailable still leaves operational row with honest drilldown failure; HP/conditions do not change revision digest; corpus path/Markdown not required.

**Demolition:** Replace `addGeneratedStatblockToCombat` artifact/corpus identity for the normal path; delete old path if no named consumer.

**Stop conditions:** existing combat persistence cannot version the locator without destructive migration; initiative modifier derivation is ambiguous under contract; tracker assumes Markdown is canonical.

**Named successor:** Campaign Supergraph PR009 / Play projection migration uses this adapter.

## 15. SBW14 — Image generation, selection, and binding

**Status:** BLOCKED on SBW04; parallel thereafter.

**Mission:** Request optional image generation through DungeonMindServer, display typed partial outcomes, and let the GM select/bind CDN assets to Threat or statblock form roles.

**Invariant:** Media is durable presentation state with provider-owned asset identity; it is not mechanics and cannot invalidate otherwise accepted mechanics.

**Deliverables:** generate-images option/action; asset brief review; candidate assets/warnings; selection model; Threat vs binding/form role choice; exact CDN refs; reload; shared renderer media slots; safe delete/unbind semantics.

**Non-goals:** 3D, local binary storage, deleting by arbitrary URL, mechanics digest change, blocking candidate generation on image failure.

**Acceptance:** unconfigured generator returns typed warning; successful asset has durable ID/CDN URL; selection survives reload; changing portrait/token leaves revision digest unchanged; one asset can have variants; credentials remain server-side.

**Demolition:** Remove any data-URI or transient provider URL used as a durable statblock image where replaced.

**Stop conditions:** asset contract lacks ownership-safe delete/unbind; generated URL is not durable; UI needs untyped provider-specific payloads.

**Named successor:** `SBW15`.

## 16. SBW15 — 3D media contract and job pipeline

**Status:** DEFERRED until SBW14 dogfood and provider selection.

**Mission:** Define and prove a separate model-asset contract and asynchronous job lifecycle for generated 3D assets without widening image-only `AssetRefV1` dishonestly.

**Invariant:** A 3D model is a typed media resource with durable files, preview, lineage, and job state—not an image URL with a different extension.

**Deliverables:** provider/use-case decision; media contract; formats/MIME; preview relationship; job lifecycle; CDN/storage; validation; one fixture/proof path. Implementation may be design-only if no provider is selected.

**Non-goals:** Blocking core statblock workflow; rigging/animation/printing guarantees without a chosen use case; arbitrary file upload platform.

**Acceptance:** contract represents at least canonical model + preview + provenance + variants/job state; no use of image-only fields; ownership/deletion defined; consumer projection can decline unsupported formats honestly.

**Stop conditions:** no selected user use case or provider; storage cannot serve model MIME/range requests; licensing/retention unresolved.

## 17. Cumulative proof record

After `SBW13` and `SBW14`, add one dogfood report under `Docs/Reports/` proving the Shepherds' Flock scene workflow end to end. This report is evidence, not a replacement for per-PR tests or roadmap authority.
