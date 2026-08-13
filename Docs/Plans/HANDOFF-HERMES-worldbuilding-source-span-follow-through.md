---
pr_body_template: |
  ## Handoff pointer
  - Conversation: CON-READY
  - Flow / agent: HERMES
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-HERMES-worldbuilding-source-span-follow-through.md`
  - Branch: `agent/con-ready-hermes-source-span-follow-through`

  ## Verification pointer
  - Base: `9cafa3170d9d15789a8ffed5243f348683f4e848`
  - Merged predecessor: PR #569 (`BUILD: open graph evidence in source`)
  - Verification: see §8 and the latest numbered review handback

  The checked-in handoff, cumulative diff, nano commits, numbered review
  handback, and independently rerun verification are the review contract. The PR
  description is transport metadata only.
---

# HANDOFF — HERMES: Worldbuilding source-span follow-through

**Created:** 2026-08-12.  
**Status:** ACTIVE — dispatch exactly one implementation capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-HERMES-worldbuilding-source-span-follow-through.md`  
**Conversation / workstream:** `CON-READY`  
**Flow / agent:** `HERMES`  
**Handoff direction:** `DESIGN → CODE`  
**Implementation branch:** `agent/con-ready-hermes-source-span-follow-through`  
**PR title:** `HERMES: read admitted worldbuilding source spans`  
**Base:** `main` at `9cafa3170d9d15789a8ffed5243f348683f4e848` (PR #569 merge)  
**Merged predecessor:** PR #569 — `BUILD: open graph evidence in source`  
**Roadmap slice:** `CR03A — admitted worldbuilding source-span follow-through`  
**Primary CON-READY user story:** `CR-U6 — Hermes follows admitted provenance into source when the graph is not enough`  
**Secondary CON-READY user stories advanced:** `CR-U7 — graph facts and richer source detail remain truthfully distinct`; `CR-U16 — navigation is part of the answer`  
**Candidate successor after re-anchor:** `CR03B — bounded same-artifact source follow-through/search`, **only if post-merge dogfood still shows CR-U6 is materially false after exact-span reading**.

> **Dispatch rule:** This checked-in handoff is authoritative once present on the implementation branch. The worker must not compress, replace, rewrite, or substitute it with a shorter PR description before implementation.
>
> **One-capability rule:** This PR makes one already-admitted worldbuilding evidence span readable by Hermes through the existing `read_graph_source` authority. It does **not** add generic source search, artifact browsing, arbitrary Markdown access, or a second source-navigation authority.
>
> **Review-count rule:** The first implementation review is `Review Cycle 1`. Every later formal review increments exactly once, whether PASS or CHANGES REQUESTED. Fix commits, handbacks, comments, CI reruns, and evidence-only posts do not increment the cycle until another formal review is submitted.

---

# §0 CON-READY pickup and product framing

The implementation handoff must begin from the product story, not from the retrieval architecture.

## Primary CON-READY user story/stories

- **CR-U6:** I can ask Hermes about a known world object; if the graph does not contain enough detail, Hermes can follow admitted provenance into the exact source that supports that object.
- **CR-U7 (advanced, not necessarily completed):** Hermes can use richer source-only detail without silently relabeling that detail as a durable World Graph fact.
- **CR-U16 (advanced):** The answer can carry useful provenance/citation navigation rather than merely saying that provenance exists.

## Current user-visible failure

PR #569 made the human path work:

```text
World Graph object
→ explicit evidence row
→ Read source
→ server re-resolves SourceArtifact A + SourceSpan S
→ Build opens the exact admitted source passage when bytes still match
```

Hermes does **not** yet have the equivalent worldbuilding source passage capability.

The current Hermes tool surface already contains `read_graph_source`, and it is correctly bounded to source anchors admitted into the active `GraphRetrievalSession`. But the current World Graph retrieval source reader recognizes only:

```text
repo://... + heading:<exact heading>
graph-data://... + jsonptr:<pointer>
```

CR02A/#567 worldbuilding contributions preserve their evidence differently:

```text
EvidenceRef.source_span_ref_id = S
→ durable graph evidence.source_span_ref_id = S
→ for sessionless worldbuilding evidence, evidence.locator = S
```

`S` is an opaque persisted SourceSpan identity, not a `heading:` locator. Therefore a real source-backed worldbuilding graph object can expose a source anchor to Hermes but that anchor is currently classified as unsupported/unreadable for source reading. Hermes can find the object and its graph claims, but cannot read the exact richer paragraph that the GM can now open through #569.

That is the first CR03 blocker.

## One independently useful outcome after this PR

For a real Glass Orchard object such as Hesta (or another source-backed object from the same one-shot if Hesta's exact evidence is unsuitable), the GM can ask Hermes for a concrete detail that exists in the admitted evidence paragraph but was not promoted into graph claims:

```text
GM question
→ Hermes finds Hesta in the World Graph
→ graph identity/claims are insufficient for the requested detail
→ graph retrieval admits anchor G for worldbuilding SourceArtifact A / SourceSpan S
→ Hermes calls existing read_graph_source with G
→ server re-resolves G, A, and S
→ exact digest-matching S text is returned
→ Hermes answers with the source detail + source citation
```

The GM does not need an artifact ID, SourceSpan ID, workspace document ID, repository path, or terminal.

## What remains false afterward

Do **not** claim all CR03/CR-U6 is complete merely because exact-span reading works.

Still false unless independently proven after merge:

- arbitrary search across the rest of A when the admitted S itself does not contain the answer;
- semantic/vector search inside A;
- browsing or enumerating other SourceArtifacts;
- historical rendering of an old worldbuilding artifact after its mutable source bytes drift;
- sentence-by-sentence automatic classification of mixed Hermes prose as graph fact vs source-only detail;
- turning a source-only detail into a durable graph claim without the normal human-governed graph write path;
- Hermes writes or source edits;
- CR04 mechanics enrichment;
- CR05 Playable Layer / live-play authority;
- arbitrary files, corpus indexes, workspace document browsing, or filesystem access.

## Real one-shot dogfood proof

Use the actual post-#567 Glass Orchard world and source material. Before implementation, identify one real worldbuilding evidence span where:

1. an admitted graph object exists;
2. its evidence points to a real `worldbuilding` SourceArtifact A and SourceSpan S;
3. the source paragraph contains a concrete GM-useful detail;
4. that detail is **not** already present as an accepted graph claim used to answer the question.

Prefer Hesta because she has been the CON-READY continuity object. If Hesta does not satisfy all four facts, choose another real Glass Orchard object and record why. **Do not create or tailor a new fixture to make the live dogfood pass.**

The dogfood must show the pre-change unreadable/unsupported behavior and the post-change exact source read, answer, citation, drift failure, and no graph mutation described in §8.4.

---

# §1 Mission and merge-ready invariant

## 1.1 Mission

> **As a GM asking Hermes about a known source-backed world object, I can get a useful answer from the exact worldbuilding evidence passage admitted by that object's graph provenance when the graph claims alone do not contain the requested detail.**

## 1.2 Merge-ready invariant

> **For one active GraphRetrievalSession R and one opaque source anchor G already admitted by R, Hermes may request source reading only by G (plus the existing bounded max-character control). DungeonBuddy re-resolves G against R's exact world/campaign/focus/admissibility/revision, derives the graph-admitted worldbuilding SourceArtifact A and persisted SourceSpan S server-side, re-resolves A and S through the server-owned SourceArtifact/SourceSpan registries, and returns text only when the current repo-relative source bytes still match A's admitted digest and S still belongs to that exact artifact revision. A missing or foreign anchor, mismatched A/S, non-worldbuilding or unsupported provenance, missing registry lineage, source drift, digest mismatch, path escape, unavailable span, stale/foreign retrieval session, or caller-supplied artifact/span/path authority fails closed without widening to another artifact, searching the corpus/filesystem, mutating graph/source state, or manufacturing graph claims from source-only prose. A successful read is recorded only as a bounded SourceRead/source citation tied to G/A/S and the exact returned line range.**

Every changed layer and acceptance claim must reduce to this invariant.

## 1.3 What becomes true

After merge:

- current worldbuilding graph evidence with persisted `source_span_ref_id` is a supported Hermes source-reading shape;
- the model-visible tool remains `read_graph_source`; no second generic source browser is introduced;
- the model presents only an admitted anchor ID, never A/S/path as source authority;
- server-side graph re-resolution proves G is still admitted in the exact retrieval snapshot;
- server-side SourceArtifact/SourceSpan registry resolution proves A/S identity and digest lineage;
- the exact source span can be returned with bounded text, content digest, and returned line range;
- successful reads create `SourceReadEntry` / `SourceCitation` evidence through the existing answer-grounding path;
- source-only prose does not become a graph claim merely because Hermes read it;
- source drift fails closed instead of applying S to changed bytes.

## 1.4 Pre-dispatch critique

| Question | Answer |
|---|---|
| Why not create `search_source` now? | Because the first broken observable is simpler: the graph already names the exact supporting worldbuilding span and Hermes cannot read it. Whole-artifact search would add discovery authority before the admitted passage itself works. |
| Why reuse `read_graph_source`? | It already has the correct model authority: active retrieval session + admitted opaque anchor. A new tool that accepts artifact/path/span would widen authority for no product benefit. |
| Why not parse A/S from `evidence_ref_id` or from the stable span string? | Those IDs are identities, not caller-controlled encoding contracts. A/S/S line bounds must be re-resolved from explicit persisted graph/registry records. |
| Why not trust A/S copied into the retrieval-session packet? | The session is useful continuity state, not the final authority. The source read must re-resolve G against the exact graph revision before opening source bytes. |
| Why not use the Build `/source-navigation` endpoint from Hermes? | That endpoint is a browser navigation contract and returns route/document state. Hermes needs source content under graph-session authority, not a simulated browser hop. Reuse its underlying SourceArtifact/SourceSpan integrity rules, not its URL contract. |
| Why not read the current workspace document after drift? | The old graph provenance names immutable artifact revision A. Current changed bytes are not A. Without historical byte storage, truthful behavior is a source-integrity/stale failure. |
| Can source-only detail become graph canon? | No. Successful reading creates SourceRead/citation evidence only. Durable graph claims remain governed by existing graph publication/write authority. |
| What is the likely catastrophic bug? | An admitted G for A/S is used as a doorway to arbitrary repo files or to current changed A bytes, allowing Hermes to answer from material the graph never admitted. |
| What fact forces a stop? | If the current graph no longer preserves explicit `source_span_ref_id` for #567 worldbuilding evidence, or if implementing this requires parsing opaque IDs instead of explicit provenance, stop and repair that provenance seam first. |

---

# §2 Current repository ground truth

Implementation must begin from these facts on `main` at `9cafa317…`.

## 2.1 Existing Hermes authority is already narrow enough

`read_graph_source` currently accepts model-visible:

```text
retrievalSessionId   # injected by capability policy / active turn
anchorIds            # 1..8 opaque source anchors already admitted into R
maxChars             # bounded
```

It does **not** accept:

```text
path
uri
workspaceDocumentId
sourceArtifactId
sourceSpanRefId
worldId / campaignId / revision override
```

Preserve that model-visible contract. Extra caller fields remain forbidden.

## 2.2 Graph source anchors are re-derived from exact revision authority

World Graph retrieval loads one exact revision-pinned projection/store and deterministically derives anchors from active assertion support → evidence → SourceArtifact. Anchor identity includes world, campaign, focus, admissibility, revision, evidence, SourceArtifact, and locator identity.

A source read re-derives the anchor in the same exact context. Foreign or unknown anchors already fail closed.

Keep that as the first authorization boundary.

## 2.3 Worldbuilding evidence carries an explicit persisted SourceSpan

The CR02A candidate→contribution path requires each worldbuilding evidence ref to carry `source_span_ref_id`. For sessionless worldbuilding evidence it also persists that span ID as the evidence locator.

The graph therefore has the right durable pointer. Do not manufacture a heading locator and do not infer line numbers from prose.

## 2.4 The current source reader cannot interpret that pointer

The current retrieval source reader supports:

- `repo://` + exact Markdown heading;
- `graph-data://` + JSON pointer.

It explicitly has no general file-reader fallback. SourceSpan IDs therefore land in the existing `unsupported` path today.

This PR adds one exact, registry-backed worldbuilding SourceSpan read path. It must not weaken the two existing locator families.

## 2.5 #569 already established the correct A/S integrity semantics

The merged source-navigation resolver demonstrates the required rules:

- SourceArtifact A must be `worldbuilding`;
- A carries durable workspace-document lineage in the server-owned registry;
- SourceSpanIndex is loaded by A and validated against A's exact digest;
- S is selected by exact `source_span_ref_id`, never first-span fallback;
- current saved source digest must equal A for exact passage use;
- drift is truthful stale state with no old highlight.

Hermes must reuse these integrity facts. Do not call the browser route or import frontend concepts.

## 2.6 Existing source citation projection is already useful

A successful `read_graph_source` appends `SourceReadEntry` with:

```text
source_read_id
anchor_id
outcome
content_sha256
line_start / line_end
truncated
source_artifact_id
```

The answer validator emits `SourceCitation` only for successful opened reads. Product acceptance keeps graph references and source citations distinct.

That is enough for this slice to advance CR-U7 without inventing a second answer ledger.

## 2.7 Existing answer grounding is deliberately conservative

The current validator does not bless arbitrary model prose as new durable graph facts. Source reads can make an answer `source_verified`, while graph claim authority remains separately represented.

This PR may adjust small metadata plumbing needed to carry exact span provenance, but it must not rewrite the answer-grounding model or treat source text as a graph claim.

---

# §3 Observable paths and adversarial sequences

## 3.1 Observable path inventory

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| Hermes graph object → worldbuilding anchor | anchor can be admitted but SourceSpan locator is unsupported/unreadable | anchor explicitly carries/retains the admitted worldbuilding span identity needed for server follow-through | Kernel retrieval result + retrieval session |
| `read_graph_source(G)` | graph re-resolves G, then returns unsupported locator for SourceSpan-backed worldbuilding evidence | same tool re-resolves G → A/S, reads exact S through registry/digest authority, returns bounded content | retrieval service + SourceArtifact/SourceSpan reader |
| successful source read | no worldbuilding SourceSpan content, therefore no source citation | append normal SourceRead; answer can emit normal SourceCitation with A/digest/lines | interaction executor + answer validator |
| source drift after graph admission | worldbuilding span still appears in graph but old bytes no longer exist at mutable path | fail `source_integrity_error`/equivalent, return no changed prose and no source citation | worldbuilding source-span read service |
| foreign anchor from another R/revision | denied/empty through current graph/session authority | remains denied; must not use registry A/S to bypass session admission | executor + graph re-resolution |
| model supplies A/S/path extras | currently strict schemas forbid extras | remains invalid arguments; no new caller authority | tool/request schema |
| old heading/json-pointer anchors | currently supported | no regression | Kernel source reader |
| mixed batch | current batch can contain multiple admitted anchors | supported old locators and exact worldbuilding spans each resolve independently; one failure must not silently substitute another anchor | executor batch behavior |

## 3.2 Required adversarial sequences

| Sequence | Required safe result |
|---|---|
| R admits G1→A/S1 and G2→A/S2 → model requests G2 | exact S2 text; never first-win S1 |
| R1 admits G → R2 tries G without admission | denied as `anchor_not_in_session` or equivalent; registry lookup cannot override |
| graph G re-resolves to A/S but session metadata claims A2/S2 | graph re-resolution wins; mismatch fails closed, not silently rebound |
| caller adds `sourceArtifactId`, `sourceSpanRefId`, `path`, `uri`, or line numbers | invalid arguments; values never influence resolution |
| graph A/S valid → registry A missing/foreign/mismatched | fail closed, no file access |
| graph A/S valid → span index contains S for B or different digest | fail closed, no fallback to another span |
| exact A/S → normal Build save changes current source → old G read | source-integrity/stale failure, zero returned changed-source content, zero source citation |
| A URI attempts `../` or absolute path | path escape/unsupported failure, no leaked resolved path |
| S points at lines after YAML frontmatter | returned lines use full saved-Markdown numbering; no body-relative offset invention |
| maxChars truncates S | `truncated` true and returned line range describes returned text only; no claim that unread bytes were read |
| source-only detail returned | claim ledger does not gain a new factual GraphClaim solely from the read; source citation records the source authority |
| repeated exact read | read-only/idempotent with respect to graph revision, SourceArtifact registry, SourceSpan index, and Markdown bytes |

---

# §4 Files in scope (allowlist)

Keep the implementation inside the existing retrieval → session → Hermes chain. No frontend file and no new HTTP route is expected.

## 4.1 Production paths

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/graph_memory/retrieval/models.py` | Preserve explicit SourceSpan identity on admitted/read source-anchor response models; if a `source_span` locator kind is introduced, make it explicit and typed. |
| Modify | `src/graph_memory/kernel/world_retrieval.py` | Re-derive G→evidence→A/S under the exact graph snapshot and expose explicit source-span metadata without parsing opaque IDs. Preserve existing heading/json-pointer behavior. |
| Modify | `apps/live_control_server/services/world_graph_retrieval.py` | Compose graph-anchor authority with server-owned worldbuilding SourceArtifact/SourceSpan reading; no browser route or caller path authority. |
| Create or modify | `apps/live_control_server/services/worldbuilding_source_span_read.py` **or** the smallest equivalent server-owned service | Re-resolve registry A/S, verify graph-vs-registry identity/digest/scope, verify current bytes, and return exact bounded S content. Prefer a focused service over adding browser concerns to `source_navigation.py`. |
| Modify if useful | `src/graph_memory/retrieval/source_reader.py` | Add only a safe digest-verified repo-relative line-span primitive if needed; it must remain authorization-neutral and must not become a generic exposed file reader. |
| Modify | `src/graph_memory/interaction/session.py` | Preserve explicit admitted source-span metadata only if required for Hermes/session continuity; do not turn session metadata into final authority. |
| Modify if session shape changes | `src/graph_memory/interaction/session_hydrate.py` | Round-trip the exact added anchor metadata across the process boundary, fail closed on malformed rows. |
| Modify | `src/graph_memory/interaction/expansion_executor.py` | Keep `read_graph_source` model args unchanged; record successful worldbuilding span reads through existing SourceRead/operation paths. |
| Modify | `apps/live_control_server/services/hermes_graph_interaction_tools.py` | Clarify tool description that an admitted worldbuilding span is readable source provenance; do not add a new generic source tool. |
| Modify only if a Kernel public helper is factored | `src/graph_memory/kernel/__init__.py` | Export one explicit anchor-resolution helper if required. Do not export storage internals. |

### Expected unchanged production paths

These should normally require **no** production change:

- `src/graph_memory/hermes_graph_plugin.py` — tool name and policy remain the existing `read_graph_source` authority;
- `apps/live_control_server/services/hermes_graph_agent_contract.py` — no new tool-event authority should be necessary unless explicit source-span metadata must cross this boundary;
- `apps/live_control_server/services/hermes_graph_query.py` — current SourceRead → SourceCitation acceptance path should already work;
- `apps/live_control_server/routes/world_graph_retrieval.py` — existing route may gain behavior through its service but no new route is needed;
- any frontend file.

If implementation proves one of these expected-unchanged seams requires a small owning change, use the bounded-discovery rule below and explain why in the handback.

## 4.2 Test paths

Expected owning tests:

- `tests/test_graph_kernel_world_retrieval.py`
- `tests/test_world_graph_retrieval_routes.py`
- `tests/test_graph_retrieval_interaction.py`
- `tests/test_hermes_graph_agent.py`
- `tests/test_live_query_hermes_graph.py`
- `tests/test_source_artifact.py`
- `tests/test_source_span_contract.py`

A single new focused test such as `tests/test_hermes_worldbuilding_source_span.py` is allowed if it materially reduces fixture duplication and proves the cross-layer invariant better than forcing everything into existing files.

## 4.3 Bounded discovery exception

Up to **3 additional existing test/helper/registration paths** may be changed when current code structure makes an owning proof impossible in the named files. They must:

1. be directly required by this capability;
2. add no second public authority;
3. be named explicitly in the handback with why they were necessary.

Any additional production path beyond the table above is a stop-and-reconcile event unless it is a trivial import/export registration seam.

---

# §5 Exact contract

## 5.1 Model-visible tool contract stays the same

Do **not** add a model argument for A, S, path, URI, document ID, or line numbers.

The governed request remains conceptually:

```json
{
  "schema": "dmb_read_graph_source_request_v1",
  "retrievalSessionId": "<server-injected active R>",
  "anchorIds": ["<G>"],
  "maxChars": 4000
}
```

`anchorIds` remain opaque graph-admitted capabilities. `maxChars` remains bounded by the existing hard maximum.

Unknown extra fields remain rejected by `extra="forbid"`.

## 5.2 Graph-side G→A/S resolution

For each requested G:

1. Load active retrieval session R.
2. Require G is already in R's admitted source-anchor set.
3. Reconstruct the exact retrieval request context from R's snapshot:
   - world;
   - campaign;
   - focus;
   - admissibility;
   - revision pin;
   - scope mode.
4. Re-resolve G against the exact graph revision/projection support chain.
5. Obtain the exact evidence row E, SourceArtifact ID A, source domain, and explicit `source_span_ref_id=S` from persisted graph evidence.
6. Never parse A/S from `evidence_ref_id`, anchor text, display label, URI, or SourceSpan string formatting.
7. If G no longer resolves to the same admitted provenance in R's snapshot, fail closed.

The implementation may factor an internal Kernel helper so G resolution is not duplicated. Do not expose graph-store internals to the Hermes layer.

## 5.3 Worldbuilding A/S registry resolution

The SourceSpan follow-through path applies only when the re-resolved graph provenance says:

```text
source_domain == "worldbuilding"
source_span_ref_id is present
```

Then server-side code must:

1. load registry SourceArtifact A by exact ID;
2. require registry A is `worldbuilding`;
3. require graph A and registry A agree on the immutable identity facts available at both boundaries, at minimum source artifact ID and content digest; also compare URI/world/campaign where both are present;
4. load A's persisted SourceSpanIndex;
5. validate the index against A's exact content digest;
6. locate exact S by `source_span_id`; no first-span fallback;
7. require S's `source_artifact_id` and digest equal A;
8. resolve the repo-relative source path only from server-owned A.uri / lineage;
9. verify current file bytes hash to A's digest **before** slicing S;
10. return only S's full-source line interval, bounded by `maxChars`.

Missing registry data is not permission to fall back to the graph artifact URI alone.

## 5.4 Existing locator families stay intact

Heading and graph-data JSON-pointer anchors continue through the existing behavior.

Do not convert them into SourceSpan IDs and do not route them through the worldbuilding registry unnecessarily.

A batch may contain mixed locator families. Each requested G is resolved independently and in request order.

## 5.5 Read response

Use the existing `dmb_world_graph_source_anchor_read_v1` response shape where possible. Add only explicit optional SourceSpan identity metadata needed to prove the new contract.

Successful worldbuilding span read must include enough information for the existing SourceRead/citation path:

```text
outcome = enough | truncated
anchorId = G
sourceArtifactId = A
sourceDomain = worldbuilding
sourceSpanRefId = S          # if added to public response model
content = exact returned text
contentSha256 = A digest / verified current-byte digest
lineStart = exact full-Markdown returned start
lineEnd = exact full-Markdown returned end
truncated = bool
```

Do not return filesystem paths, workspace paths, registry paths, or SourceSpan index paths.

## 5.6 Drift behavior

If current bytes no longer equal A:

- do not read S from the current changed bytes;
- do not search for similar prose;
- do not silently create a new SourceArtifact;
- do not follow current workspace revision;
- return a stable integrity/stale failure with no content and no successful SourceRead citation.

The preferred stable diagnostic is the existing `source_integrity_error` family unless a more specific already-established source-stale code is demonstrably the repository convention.

Historical worldbuilding bytes are not currently a durable source archive. Do not invent one in this PR.

## 5.7 Source-only answer authority

A successful source-span read may support a Hermes answer detail that is not a graph claim.

Required authority behavior:

- reading source does **not** append a new `GraphClaim`;
- graph identity/facts used for discovery remain graph references;
- source content is represented through SourceRead/SourceCitation;
- `source_verified` is allowed when existing answer validation requirements are met;
- no sentence-level “graph fact” label may be inferred merely because a source citation exists;
- if the current validator cannot safely accept the mixed answer without granting graph authority to source-only text, stop and report the exact validator gap rather than weakening claim validation.

This slice advances CR-U7 through distinct graph/source evidence channels; it does not need to solve sentence-level attribution UI.

## 5.8 Read-only semantics

The read path must not mutate:

- World Graph head/revision/store;
- graph claims or assertion support;
- SourceArtifact registry;
- SourceSpan indexes;
- workspace Markdown;
- workspace document revision;
- world/container registry.

Expected retrieval-session mutations are limited to normal turn-local evidence state:

- mark admitted anchor opened/readable when successful;
- append SourceReadEntry;
- append source_read operation event.

---

# §6 Required proofs by owning boundary

## 6.1 Kernel / graph provenance proof

Prove:

- worldbuilding evidence's explicit S survives anchor derivation;
- G is deterministic and revision/scope bound as before;
- G2/S2 resolves exactly even when A also has S1;
- foreign revision/context G does not resolve;
- no parsing of opaque evidence/anchor/span IDs supplies line authority;
- existing heading/json-pointer anchors retain behavior.

## 6.2 SourceArtifact / SourceSpan reader proof

Build a synthetic committed worldbuilding source with:

- YAML frontmatter;
- at least two separated paragraph spans S1/S2;
- a registry A bound to exact digest;
- a persisted SourceSpanIndex.

Prove:

- exact S2 returns S2 lines, not S1;
- full-source line numbers remain correct across frontmatter;
- maxChars truncation reports only returned extent;
- A + span belonging to B fails;
- index digest mismatch fails;
- current source digest mismatch fails before text is returned;
- path traversal/absolute path never escapes repo root;
- no-match/missing S does not guess.

## 6.3 Retrieval session / process-boundary proof

If SourceAnchorState gains A/S metadata, prove it round-trips through `project_for_hermes` → hydrate without invention or loss.

Regardless of packet shape, prove final reading authority still re-resolves G against the graph revision instead of trusting packet A/S.

Required adversarial test: corrupt/forge packet-side A/S metadata while keeping G constant; either hydration rejects it or graph re-resolution detects mismatch and fails. It must never redirect G to the forged source.

## 6.4 Hermes interaction proof

Prove `read_graph_source` still accepts only R + G + maxChars and:

- reads admitted exact worldbuilding S;
- denies a G absent from R;
- rejects caller-supplied A/S/path/line fields;
- records SourceReadEntry with A/digest/line range;
- does not add graph claims;
- mixed old-locator + source-span batches preserve order and independent outcomes.

## 6.5 Answer/citation proof

At the live-query/product response seam, prove:

- a successful worldbuilding S read can produce a source citation;
- the citation names A, G/read ID, exact digest, and returned lines through existing SourceCitation fields;
- graph references remain separately represented;
- source-only detail is not inserted into the graph claim ledger;
- denied/stale/failed read produces no successful source citation.

---

# §7 Implementation and nano-commit contract

Use small commits that tell the authority story. A strong sequence is:

1. `GRAPH: preserve worldbuilding source spans on admitted anchors`
2. `SOURCE: read exact admitted worldbuilding spans by digest`
3. `HERMES: resolve read_graph_source through exact source spans`
4. `PROOF: cover source-only answer citation and drift`

Do not bundle:

- global corpus search;
- semantic/vector retrieval;
- UI source reader changes;
- CR02B duplicate/edit UX;
- mechanics/statblock work;
- Hermes writes;
- CUTOVER/DungeonMind `thread` work;
- unrelated test cleanup unless it is an actual baseline blocker proven by base/head comparison.

The PR body remains a pointer. The checked-in handoff + cumulative code diff + nano-commit story + latest numbered handback are review authority.

---

# §8 Verification and acceptance

## 8.1 Required automated command set

From repository root:

```bash
uv run pytest -q \
  tests/test_graph_kernel_world_retrieval.py \
  tests/test_world_graph_retrieval_routes.py \
  tests/test_graph_retrieval_interaction.py \
  tests/test_hermes_graph_agent.py \
  tests/test_live_query_hermes_graph.py \
  tests/test_source_artifact.py \
  tests/test_source_span_contract.py
```

If a new focused test file is added under §4.2, include it in this exact command.

Also run:

```bash
uv run ruff check \
  src/graph_memory/retrieval \
  src/graph_memory/kernel/world_retrieval.py \
  src/graph_memory/interaction \
  apps/live_control_server/services/world_graph_retrieval.py \
  apps/live_control_server/services/hermes_graph_interaction_tools.py

git diff --check 9cafa3170d9d15789a8ffed5243f348683f4e848...HEAD
```

If repository tooling does not have Ruff configured for one of these paths, report the exact tool/config failure rather than silently dropping the gate; use the repository's established Python lint/type command if one exists at implementation time.

No frontend build is required unless the implementation unexpectedly changes frontend code; frontend production change is itself a scope-reconciliation event.

## 8.2 Baseline-failure protocol

A required command is not green merely because a failure looks unrelated.

If any required command fails on HEAD:

1. run the same command on declared base `9cafa317…` or the current-main merge-base if main has advanced;
2. record exact base/head command and failing test names;
3. fix any head-introduced failure;
4. if a required acceptance gate remains red only because of a proven baseline failure, request an explicit operator waiver.

Only the operator/user may waive a required acceptance gate.

## 8.3 Static adversarial matrix

The author handback must explicitly report results for:

- G2→S2 non-first selection;
- foreign-session G;
- foreign-revision G;
- forged packet A/S if metadata crosses IPC;
- caller-supplied A/S/path/line extras;
- graph A vs registry A mismatch;
- S belongs to B;
- span-index digest mismatch;
- current source digest drift;
- path escape;
- YAML-frontmatter line correctness;
- maxChars truncation;
- successful SourceCitation;
- failed read → no SourceCitation;
- claim ledger unchanged by source-only read;
- existing heading/json-pointer regression tests.

## 8.4 Mandatory real Glass Orchard dogfood

This is a merge gate, not optional ceremony.

### A. Establish the real pre-change failure

Against the real Glass Orchard world on the implementation environment:

1. identify Hesta or another real #567 source-backed graph object;
2. inspect the actual graph claim ledger for that object;
3. inspect the actual admitted worldbuilding evidence span;
4. choose a concrete useful detail present in S but absent from the factual graph claim ledger;
5. run the current Hermes path or the underlying current `read_graph_source` path and record that this SourceSpan-backed anchor cannot yet provide the source text (expected unsupported/unreadable behavior).

Do not modify source content to manufacture this detail.

### B. Prove the post-change user journey

With the same world/object/detail:

```text
GM asks Hermes the detail question
→ Hermes finds the object through World Graph retrieval
→ claim ledger alone does not contain the detail
→ one worldbuilding source anchor G is admitted
→ read_graph_source is invoked with G (no path/A/S)
→ exact S content is returned
→ Hermes answers the requested detail
→ product response carries SourceCitation
```

Record:

- world/campaign/revision;
- object ID/label;
- anchor ID G;
- server-resolved A and S;
- returned line range/digest;
- source citation fields;
- graph claims before/after source read;
- graph head/revision before/after.

The answer should be useful normal prose. Do not require the GM to understand registry internals.

### C. Prove source-only truthfulness

Show that the requested detail is absent from accepted factual graph claims but present in the successful source read.

Then show:

- no new GraphClaim was created from that detail;
- the answer has source citation authority for the detail;
- graph references remain distinct from source citation records.

### D. Prove drift fail-closed using the normal product save path

After graph evidence A/S already exists:

1. open the same source in Build;
2. make and **normally save** a harmless source edit through the supported Document Save path;
3. re-run the old G source read;
4. verify it fails as stale/source-integrity mismatch;
5. verify no current changed source text is returned as though it were A;
6. verify no successful SourceCitation is created from the failed read.

If the chosen real source is lossy/save-blocked, use another real admitted Glass Orchard worldbuilding source that is saveable. Do not substitute direct file mutation unless the operator explicitly waives the normal-save dogfood step.

### E. Prove no source-discovery escalation

In the same dogfood environment, attempt at least:

- a G from another retrieval session;
- an extra `path` field;
- an extra `sourceArtifactId` or `sourceSpanRefId` field.

All must fail without opening another source.

## 8.5 No-mutation check

For read-only exact source-follow-through, compare before/after tokens/digests for the relevant:

- World Graph head/revision;
- SourceArtifact registry;
- SourceSpan index;
- source Markdown bytes (except the intentional normal-save drift subtest);
- workspace record before/after the read itself.

Turn-local retrieval-session SourceRead/operation additions are expected.

---

# §9 Stop conditions and non-goals

Stop and report instead of widening the PR if any of these facts emerge:

1. **No explicit S survives into the durable #567 graph evidence.** Repair provenance preservation first; do not parse IDs.
2. **Worldbuilding graph A cannot be reconciled with the server SourceArtifact registry A without guessing.** Resolve that identity contract first.
3. **Exact S content requires historical bytes after current source drift.** Historical SourceArtifact storage is a separate capability.
4. **The only way to make Hermes answer source-only detail is to promote it into GraphClaim authority.** Split/repair answer validation instead of weakening graph fact semantics.
5. **Reading S requires a model/client path, URI, workspace document ID, line range, or arbitrary artifact ID.** That violates the capability boundary.
6. **The implementation needs global search/index/vector retrieval to find S.** S is already admitted; that is out of scope.
7. **A current open PR has already claimed the same CON-READY Hermes source-span seam.** Re-anchor and reconcile ownership.

Explicit non-goals:

- no `search_source` / `list_source_artifacts` tool;
- no filesystem browser;
- no globbing;
- no corpus index fallback;
- no embeddings/vector database;
- no web retrieval;
- no SourceArtifact migration;
- no source edits/revert;
- no graph writes;
- no historical worldbuilding archive;
- no UI changes;
- no CUTOVER/DungeonMind work.

---

# §10 Review protocol

## 10.1 Pre-review implementation gate

The handoff-only commit does **not** consume Review Cycle 1.

Formal implementation review begins only after the branch contains actual implementation commits plus a numbered author handback. A handoff-only head is not implementation-reviewable.

## 10.2 Formal review numbering

- first formal implementation review: `Review Cycle 1`;
- next formal review after fixes/evidence: `Review Cycle 2`;
- PASS and CHANGES REQUESTED both consume the cycle number;
- commits, comments, handbacks, and CI reruns between reviews do not.

Each re-review is cumulative against this entire handoff, not only the newest commit.

## 10.3 Required finding ledger

Every author handback after a CHANGES REQUESTED review must retain each prior finding as:

```text
RC1-F1 — CLOSED / OPEN — evidence
RC1-F2 — CLOSED / OPEN — evidence
...
```

Do not erase history by presenting only the latest fix.

## 10.4 Review PASS requirements

PASS requires all of the following unless explicitly waived by the operator:

- merge-ready invariant holds;
- expected production scope remains bounded;
- graph/session/registry authority chain is fail-closed;
- required automated command set green or correctly waived under baseline protocol;
- adversarial matrix proven;
- real Glass Orchard dogfood completed;
- normal-save drift behavior proven;
- no source-discovery escalation;
- no graph/source mutation outside the intentional drift subtest;
- no current-main collision requiring re-anchor.

No GitHub Actions run is a substitute for the handoff-specific proof, and author-local proof is not a substitute for independent steward review of the cumulative diff.

---

# §11 Required author handback format

Post a top-level PR comment before requesting formal review:

```markdown
## Ready for Review Cycle N — author handback

**PR:** <url>
**Branch:** `agent/con-ready-hermes-source-span-follow-through`
**Head:** `<sha>`
**Base:** `9cafa3170d9d15789a8ffed5243f348683f4e848`

### §1 Mission (copied exactly)
> As a GM asking Hermes about a known source-backed world object, I can get a useful answer from the exact worldbuilding evidence passage admitted by that object's graph provenance when the graph claims alone do not contain the requested detail.

### §1 Merge-ready invariant (copied exactly)
> <copy §1.2 verbatim>

### Finding ledger
- <all prior RC findings, or "none — first formal review">

### Nano-commit story
1. `<sha>` — ...
2. `<sha>` — ...

### Changed paths
- <full name-only list>
- Paths outside §4: <none or exact justification under bounded discovery>

### Authority proof
- Model-visible source authority remains: R + G + maxChars only
- G re-resolves under exact graph snapshot: <evidence>
- graph A/S ↔ registry A/S exact checks: <evidence>
- drift/path/foreign failures: <evidence>

### Automated verification
```text
<exact §8.1 commands and results>
```

### Adversarial matrix
- G2/S2: ...
- foreign session/revision: ...
- forged packet metadata: ...
- caller A/S/path extras: ...
- A/S/digest mismatches: ...
- frontmatter/truncation: ...
- citation/no-citation: ...
- claim ledger unchanged: ...
- old locator regressions: ...

### Real Glass Orchard dogfood
- object/question/detail chosen: ...
- proof detail absent from graph claims: ...
- pre-change failure: ...
- post-change source read + answer: ...
- source citation: ...
- normal-save drift: ...
- no-discovery-escalation attempts: ...
- no-mutation comparison: ...

### Operator waivers
- none / <exact waiver and scope>

### Stop conditions
- none / <exact stop and why>

### Successors still false
- bounded same-artifact search (unless post-merge re-anchor proves no need)
- historical worldbuilding source browsing
- source-to-graph writeback
- CR04 / CR05
```

---

# §12 Merge and post-merge rule

This PR is not permission to auto-dispatch CR03B.

After merge:

1. re-read current `main`;
2. re-run the real one-shot source-detail journey;
3. decide whether exact-span reading makes CR-U6 sufficiently useful or whether a bounded same-artifact continuation is still a real user blocker;
4. only then design the next independently useful CON-READY slice.

The product sequence remains:

```text
ORIGINAL SOURCE
→ WORLD
→ PLAYABLE WORLD
→ PLAYED EXPERIENCE
```

Hermes source follow-through strengthens navigation between ORIGINAL SOURCE and WORLD evidence. It must not collapse source prose into World Graph canon merely because the model can now read it.
