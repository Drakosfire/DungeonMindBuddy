# STATBLOCK — HANDOFF: SBW10a exact Threat query/hydration with SBW09c2b publication-boundary hardening

**Created:** 2026-08-03
**Status:** ACTIVE — review cycle 2 REQUEST CHANGES repairs ready for re-review (PR #502).
**Flow / agent:** `STATBLOCK`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw10a-exact-threat-query-hydration-and-publication-hardening.md`
**Implementation base:** `dd1a7f2a2783e2a2fb189150bd837065122bee8f`
**Predecessor merge:** PR `#491`, merge commit `601326b03a5179682b630befd7ebbcaa761937ed`, implementation head `fe6d394e6d45a2d5e26d23e58ec2e72f68c61fb3`
**Suggested branch:** `feat/statblock-sbw10a-exact-threat-query-hydration-hardening`
**Required PR title prefix:** `statblock`

> Complete the publication write→read trust seam: harden the merged SBW09c2b failure classifications that can misstate durable publication authority, then expose one read-only SBW10a capability that queries published Threats and hydrates every returned mechanics binding from its exact immutable statblock revision. Do not build the visual Threat Sheet, edit mechanics, update bindings, place objects, or enter combat.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Harden SBW09c2b admission classification (unavailable vs mismatch vs integrity) | No alone | Yes | Backend only | Yes | Include |
| Harden SBW09c2b retry authority after c2a zero match | No alone | Yes | Backend only | Yes | Include |
| Harden committing replay reconstruction → c2a ordering | No alone | Yes | Backend only | Yes | Include |
| Reject connect-existing Threat `node` rewrites | No alone | Yes | Backend only | Yes | Include |
| Double receipt-save returns durable disk truth | No alone | Yes | Backend only | Yes | Include |
| Hermes/backend query published Threats by name/alias/role/capability/relationship | Yes | Yes | Hermes + backend API | Yes | Include |
| Hydrate every typed `uses_statblock` binding from exact DungeonMind revision | Yes | Yes | Hermes + backend API | Yes | Include |
| Build compact/full Threat Sheet UI | Yes | Yes | Yes | Yes | Named successor `SBW10b` |
| MAGIC-D3 dogfood gate (publish → query → hydrate → project) | Yes | No | Operator | Yes | Named successor after `SBW10b` |
| Plan document embed | Yes | Yes | Yes | Yes | Named successor `SBW12` |
| Mechanics edit / append revision | Yes | Yes | Yes | Yes | Named successor `SBW13` |
| Binding preference / revision adoption | Yes | Yes | Yes | Yes | Named successor `SBW14` |
| Durable object placement | Yes | Yes | Yes | Yes | Named successors `AOW03` / `AOW04` |
| Live combat adapter | Yes | Yes | Yes | Yes | Named successors `COMBAT01` / `SBW15` |

**Selected capability:** one backend + Hermes read boundary that (a) repairs merged publication failure classifications that can lie about durable authority, and (b) queries published Threats in one exact graph revision and hydrates every returned typed mechanics binding from its exact immutable statblock revision without latest, first-win, label, or corpus substitution.

**Why the included rows share one invariant:** publication write authority and read composition share the same trust seam. If admission/retry/recovery misclassifies unavailable authority as conflict, or if query/hydration silently substitutes latest mechanics, the operator cannot trust that a published Threat and its bound revision survived reload. Hardening and read composition are one write→read publication trust capability for this slice.

**Named successors:** `SBW10b` exact Threat projection; `MAGIC-D3` dogfood; `SBW12` Plan embed; `SBW13` mechanics edit; `SBW14` binding preference; `AOW03`/`AOW04` placement; `COMBAT01`/`SBW15` combat.

## §1 Mission

### Mission sentence

Hermes and backend callers can query published Threats in one exact World Graph revision and receive every typed `uses_statblock` binding hydrated from its exact immutable DungeonMind statblock revision, while merged SBW09c2b publication failures are classified from durable/readable authority rather than misstated as conflict, synthetic durable state, or silent retry.

### Invariant

```text
Every returned Threat and mechanic is attributable to one exact graph revision and one exact
(threat_node_id, binding_id, statblock_id, revision_id, definition_digest) chain; every publication,
dependency, and storage failure is classified from durable/readable authority, and no path silently
substitutes latest, first match, current head, copied mechanics, or non-durable in-memory state.
```

### Mission falsification test

```text
This is not one slice if implementation must also deliver the Threat Sheet UI, edit or append
mechanics, update binding preference, embed in Plan documents, place objects, enter combat,
generate/select media, introduce a latest/label/corpus resolver, copy mechanics bodies into the
World Graph, or generalize publication to non-Threat object types.
```

## §2 Context, authority, and boundaries

### Authority table

| Field | Required content |
| --- | --- |
| Parent authority | Roadmap Phase II `SBW10a`; tracker `SBW10a`; integration design §§8–9; merged SBW09c2b publication contract |
| Repository rules | `AGENTS.md`; service boundaries; backend-owned DungeonMind credentials; one registry / one adaptive container |
| Implementation base | `dd1a7f2a2783e2a2fb189150bd837065122bee8f` |
| Predecessor merge | PR `#491` / `601326b03a5179682b630befd7ebbcaa761937ed` / head `fe6d394e6d45a2d5e26d23e58ec2e72f68c61fb3` |
| Publication authority | SBW09a operation ledger; SBW09b identity; SBW09c1 proposal; SBW09c2a immutable lookup; SBW09c2b commit/recovery/verify |
| Binding/resource authority | SBW08 `ThreatStatblockBindingV1` / `ExternalResourceV1` |
| Exact mechanics read | SBW07 accepted revision client (`DungeonMindStatblockV1Client.get_exact_revision`) |
| Graph projection | `graph_memory.kernel.project_world_graph` with `revision_pin`; `WorldGraphProjectionRequest` |
| Hermes host | `hermes_graph_interaction_tools.py`; turn-scope inject for world/campaign/revision |
| Named successor | `SBW10b` visual projection; `MAGIC-D3` dogfood |
| What remains false | Threat Sheet UI; edit; binding writes; embed; placement; combat; media; latest resolvers |

### Read order (before code)

1. This handoff §§0–17
2. Merged SBW09c2b handoff §§6–10 (publication authority classifiers and recovery)
3. Roadmap Phase II `SBW10a` / gate ledger `MAGIC-D3`
4. `HANDOFF-pr457-sbw08-statblock-binding-contract.md` binding/resource shapes
5. `apps/live_control_server/services/threat_publication_commits.py` admission/retry/reconstruction paths
6. `apps/live_control_server/integrations/dungeonmind_statblocks/` exact-revision client
7. `src/graph_memory/projection/world_projection.py` query context and relationship views
8. `apps/live_control_server/services/hermes_graph_interaction_tools.py` tool registration pattern

### Authority precedence

When documents disagree, precedence is:

```text
1. This handoff (ACTIVE)
2. Merged SBW09c2b implementation + its tests on the implementation base
3. Roadmap / tracker sequence gates
4. Pre-designed SBW10 projection handoff (SBW10b scope only — not SBW10a query)
5. Chat memory or PR summaries
```

### Re-anchor gate

Run before branching or after any predecessor merge:

```bash
BASE=dd1a7f2a2783e2a2fb189150bd837065122bee8f
HEAD=$(git rev-parse HEAD)
test "$HEAD" = "$BASE" || {
  echo "STOP: HEAD $HEAD != implementation base $BASE"
  echo "Re-anchor against predecessor merge 601326b0 (PR #491) before dispatch."
  exit 1
}
git merge-base --is-ancestor 601326b03a5179682b630befd7ebbcaa761937ed HEAD || {
  echo "STOP: predecessor merge 601326b0 not in history"
  exit 1
}
```

Record actual base/head in the implementation PR body. Do not rewrite SHAs into this handoff after dispatch.

## §3 Current truth and post-merge defects that this PR owns

Merged SBW09c2b publication is live at PR `#491`. Review cycle 1 on PR `#502` identified publication-boundary misclassification and incomplete read semantics. This PR owns repair of F1–F5 **and** delivery of SBW10a query/hydration.

### F1 — Admission collapses unavailable deps into 409

| Aspect | Current defect | Required behavior |
| --- | --- | --- |
| Symptom | `_admit_and_build_record` treats identity/publication storage/graph unavailable like inactive/mismatch | Classify via shared `_classify_identity_authority` / `_classify_publication_operation_authority` |
| Unavailable labels | `publication_identity_storage_unavailable`, `publication_identity_graph_unavailable`, `publication_identity_busy`, publication storage unavailable | HTTP **503**; **zero** commit artifacts |
| Mismatch labels | `publication_identity_not_found`, `publication_identity_operation_not_ready`, inactive proposal, digest mismatch | HTTP **409** |
| Integrity labels | corrupt ledger, impossible reconstruction, sealed proposal mismatch | HTTP **500**; **zero** commit artifacts on failed admission |
| Proof | `test_admission_identity_storage_unavailable_no_artifacts`, `test_admission_identity_not_found_is_conflict`, `test_admission_identity_integrity_failure_no_artifacts` |

### F2 — Retry treats conclusive missing/stale as transient

| Aspect | Current defect | Required behavior |
| --- | --- | --- |
| Symptom | After c2a zero match, `publication_identity_not_found` and stable `publication_identity_operation_not_ready` become `recovery_pending` | Terminal **uncommitted** when authority is readable and conclusively missing/stale |
| Transient only | Storage/graph unavailable, lookup transient | Remain **committing** / **recovery_pending** with zero merges |
| Proof | retry matrix tests asserting label/state after zero-match c2a with readable identity authority |

### F3 — Committing replay reconstruction OSError skips c2a

| Aspect | Current defect | Required behavior |
| --- | --- | --- |
| Symptom | Reconstruction `OSError` returns early without c2a reconciliation | After lookup-key trust, run c2a even when reconstruction raises `OSError` |
| Outcome | Uncertain committing state | **recovery_pending** with retained committing record; zero duplicate merges |
| Proof | `test_committing_reconstruction_oserror_still_runs_c2a`, `test_retry_reconstruction_oserror_keeps_committing` |

### F4 — Connect-existing checks dead `node_upsert`

| Aspect | Current defect | Required behavior |
| --- | --- | --- |
| Symptom | Threat identity rewrite checks reference obsolete `node_upsert` assertion kind | Reject Threat `assertion_kind="node"` rewrites on connect-existing |
| Outcome | Silent identity drift | Integrity/conflict failure; no merge |
| Proof | connect-existing assertion tests with `node` kind on Threat assertions |

### F5 — Double receipt-save returns synthetic durable count

| Aspect | Current defect | Required behavior |
| --- | --- | --- |
| Symptom | Second receipt-save failure synthesizes `merge_attempt_count=2` or otherwise lies about disk truth | Return **last durable disk record** + typed storage failure |
| Stop-if-schema-needed | If honest durable replay requires a schema field absent from the commit record, **stop** and report the persistence gap — do not invent synthetic counters or in-memory-only authority |
| Proof | `test_double_receipt_save_failure_returns_durable_prior` |

## §4 Observable-path inventory

### 4A Publication hardening paths

| Path | Current (pre-fix) | Required | Same invariant? | Owner |
| --- | --- | --- | ---: | --- |
| Confirm admission with identity storage down | May 409 / leave artifacts | 503; no commit record | Yes | `_admit_and_build_record` |
| Confirm admission with identity not found | May recovery_pending | 409 uncommitted | Yes | admission classifiers |
| Confirm admission with integrity failure | May partial artifacts | 500; no artifacts | Yes | admission classifiers |
| Retry after c2a zero + not_found | recovery_pending | uncommitted terminal | Yes | `_maybe_retry` |
| Committing replay + reconstruction OSError | skip c2a | c2a first → recovery_pending | Yes | committing replay |
| Connect-existing + Threat node rewrite | unchecked dead path | reject `node` assertions | Yes | proposal reconstruction |
| Receipt save fails twice | synthetic count | durable prior + storage error | Yes | `_persist_committed_unverified_receipt` |

### 4B SBW10a query and hydration paths

| Path | Current | Required | Same invariant? | Owner |
| --- | --- | --- | ---: | --- |
| Direct name/alias Threat query | N/A | zero/one/many Threat hits at pinned revision | Yes | projection + `_collect_threat_hits` |
| Relationship query | N/A | Preserve connected node/edge IDs; discover Threat endpoints via admitted predicates | Yes | `_collect_threat_hits` |
| Role/threat-kind/capability context | N/A | Threat kind/role metadata in hit; no score-as-identity | Yes | projection node views |
| Focus-node anchor | N/A | `focus_node_ids` discover related Threats with `focus_node:<id>` reason | Yes | request contract |
| Zero direct matches | N/A | Empty hits when `matched_node_ids is empty` — **not** all Threats in projection | Yes | `_collect_threat_hits` |
| Related Threat discovery | N/A | `related_to_match:<node_id>:<predicate>` on admitted edges | Yes | relationship walk |
| Binding enumeration | N/A | Every outgoing `uses_statblock` edge enumerated; no first-win | Yes | `_enumerate_statblock_bindings` |
| Server unavailable | N/A | Threat identity + locators retained; mechanics `unavailable` | Yes | `_hydrate_binding` |
| Exact revision 404 | N/A | `exact_revision_missing`; no latest fallback | Yes | exact client |
| Digest mismatch | N/A | `integrity_failure`; mechanics not trusted | Yes | digest gate |
| Hermes tool answer | N/A | Read-only tool; scope injected; zero/one/many explicit | Yes | `query_threat_mechanics_hydration` |
| Graph head advance | N/A | Same `revision_pin` → same hydration chain | Yes | pin enforcement |
| Malformed binding edge | N/A | Integrity hit per edge; not silent `no_binding` drop | Yes | enumeration |

**Relationship semantics (normative — review finding 2):**

- Candidate Threat IDs come from **(a)** directly matched Threat nodes in `query_context.matched_node_ids`, **and (b)** Threat endpoints connected to matched or focused nodes through **admitted** relationships in the projection query context.
- Each relationship-derived hit carries match reason `related_to_match:<node_id>:<predicate>`.
- When `query_context` exists and `matched_node_ids is empty` with no `focus_node_ids`, the response is **zero hits** — never enumerate every Threat node in the projection.

## §5 Files in scope — allowlist

Default deny everything not listed. No edits outside this allowlist without stop report.

### 5A Required existing paths

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live_control_server/services/threat_publication_commits.py` | F1–F5 publication hardening |
| Modify | `tests/test_threat_publication_commits.py` | F1–F5 regression matrix |
| Modify | `tests/test_threat_publication_commit_api.py` | HTTP mapping only if existing labels insufficient |
| Modify | `apps/live_control_server/routes/threat_publication_commits.py` | Route mapping only if label→status insufficient |

### 5B New SBW10a read boundary

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `apps/live_control_server/models/threat_query_hydration.py` | Strict request/response/hit/binding models |
| Create | `apps/live_control_server/services/threat_query_hydration.py` | Query + enumerate + hydrate orchestration |
| Create | `apps/live_control_server/routes/threat_query_hydration.py` | `POST /api/live/threats/query-hydration` |
| Modify | `apps/live_control_server/main.py` | Router registration only |
| Create | `tests/test_threat_query_hydration.py` | Service owning-boundary tests |
| Create | `tests/test_threat_query_hydration_api.py` | Route contract tests |
| Modify | `apps/live_control_server/services/hermes_graph_interaction_tools.py` | `query_threat_mechanics_hydration` tool |
| Modify | `src/graph_memory/hermes_graph_plugin.py` | Capability rule for new tool |
| Modify | `tests/test_hermes_graph_agent.py` | Tool registration + scope inject tests |
| Modify | `tests/test_live_query_hermes_graph.py` | Hermes integration only if tool wiring requires |

### Bounded discovery exception

```text
Directory roots:
  apps/live_control_server/services/world_graph_projection.py
  apps/live_control_server/integrations/dungeonmind_statblocks/
  apps/live_control_server/services/hermes_graph_agent_host.py
  src/graph_memory/projection/world_projection.py

Maximum additional production paths: 8
Maximum additional test paths: 8
Allowed kinds: exact projection adapter call, exact DungeonMind client method reuse,
  Hermes host registration hook, focused route/error mapper, prohibition-search tests
Decision rule: include only when SBW10a query/hydration cannot compile or verify without it
Scope rule: no refactors, no prompt edits, no unrelated Hermes behavior changes
Required report: list every discovered path in PR handback with one-line necessity proof
```

## §6 Explicitly out of scope

| Capability | Why excluded | Owner |
| --- | --- | --- |
| Threat Sheet / compact-full UI projection | Read composition only; visual surface is `SBW10b` | `SBW10b` |
| Binding preference / primary selection writes | Read-only; no graph mutation | `SBW14` |
| Mechanics edit / append revision | Authoring lane | `SBW13` |
| Plan Markdown/Tiptap embed | Document surface | `SBW12` |
| Plan document content hydration re-audit | Separate gate | `SBW11` |
| Durable object placement | Requires query + projection dogfood | `AOW03`/`AOW04` |
| Live combat insertion | Requires exact seed contract | `COMBAT01`/`SBW15` |
| Image generation/selection | Media lane | `SBW16`–`SBW17` |
| Latest/label/corpus statblock resolver | Prohibited substitution | never |
| Copy mechanics bodies into World Graph | Mechanics stay in DungeonMind | never |
| Generic non-Threat publication | Threat-only slice | later successors |
| Workbench confirmation UI | Publication input surface | separate bite |
| Graph Kernel write/CAS changes | Consumes public Kernel APIs only | never |

## §7 Implementation contract

### 7A Publication classification (ok / mismatch / unavailable / integrity)

Admission, retry, and route mapping must preserve this taxonomy:

| Class | Example labels | HTTP | Durable artifacts |
| --- | --- | ---: | --- |
| ok | committed-verified, committed-unverified, uncommitted (terminal) | 200/409 per state | Honest record |
| mismatch | `publication_identity_not_found`, inactive proposal, digest mismatch, zero-match c2a with readable authority | 409 | No false committing claim |
| unavailable | `publication_identity_storage_unavailable`, graph/storage unavailable, transient lookup | 503 | Retained committing only when honest |
| integrity | corrupt ledger, impossible reconstruction, manifest contradiction | 500 | No synthetic recovery |

Shared classifiers `_classify_identity_authority` and `_classify_publication_operation_authority` are the single source of truth. Admission must not inline a weaker subset.

### 7B Query request contract

`ThreatQueryHydrationRequestV1` (`dmb_threat_query_hydration_request_v1`):

| Field | Required | Rule |
| --- | ---: | --- |
| `world_id` | yes | Exact world scope |
| `campaign_id` | yes | Exact campaign scope |
| `revision_pin` | yes | Exact immutable graph revision; **no current-head default** |
| `query_text` | yes | Hermes/caller search text |
| `focus_node_ids` | no | ≤8 exact anchor node IDs for relationship discovery |
| `relationship_predicates` | no | ≤16 admitted predicate filters (case-insensitive) |
| `max_hits` | no | 1–64; default 16 |
| `include_mechanics` | no | default true |

Relationship discovery inputs:

- Direct Threat matches from projection `query_context.matched_node_ids`.
- Related Threat endpoints via admitted edges from matched **or** focus anchors.
- Match reason for relationship hits: `related_to_match:<node_id>:<predicate>`.
- Empty `matched_node_ids` with empty `focus_node_ids` ⇒ zero hits (not all Threats).

### 7C Query response contract

`ThreatQueryHydrationResponseV1` (`dmb_threat_query_hydration_response_v1`):

| Field | Rule |
| --- | --- |
| `revision_id` | Must equal requested pin / projection snapshot |
| `result_label` | `ok` family: `threat_query_hydration_ok` / `_partial` / `_empty`; failures typed |
| `hits[]` | Zero/one/many; deterministic sort by `(label.casefold(), node_id)` |
| `hits[].threat` | `WorldGraphProjectionNodeView` |
| `hits[].match_reasons[]` | Includes direct, `focus_node:`, and `related_to_match:` reasons |
| `hits[].relationships[]` | Edges involving the Threat node (IDs preserved) |
| `hits[].bindings[]` | One entry per enumerated `uses_statblock` edge |
| `hits[].mechanics_disposition` | Aggregated per hit |
| `diagnostics[]` | Bounded opaque strings; no mechanics bodies |

### 7D Binding enumeration and hydration steps

For each Threat hit:

1. Enumerate **every** outgoing `uses_statblock` relationship where the Threat is the source endpoint and direction is outgoing.
2. Parse typed `ThreatStatblockBindingV1` from the edge; malformed edges become integrity bindings with messages — never silent drop.
3. Verify external resource node/provider agreement with binding statblock identity.
4. If `include_mechanics` and binding is well-formed, call `DungeonMindStatblockV1Client.get_exact_revision(statblock_id, revision_id)` only.
5. Compare returned definition digest to binding `definition_digest`; mismatch ⇒ `integrity_failure`.
6. Never copy mechanics JSON into graph storage or response graph fields beyond the typed revision resource envelope.

### 7E Zero/one/many semantics

| Dimension | Rule |
| --- | --- |
| Threat hits | Explicit list; may be empty; never implicit single winner |
| Bindings per Threat | All enumerated; UI/Hermes must not pick first list item |
| Shared mechanics | Two Threats may reference same `(statblock_id, revision_id, digest)` with distinct identities |
| Multiple eligible primaries | Return all; do not auto-select; `SBW10b` owns selection UX |
| Empty search context | Zero hits when no matched/focus anchors |

### 7F Hermes integration contract

- Tool name: `query_threat_mechanics_hydration`
- Read-only: no graph writes, no publication calls, no mechanics mutation
- Server injects authoritative `world_id`, `campaign_id`, `revision_pin` from turn policy — model must not invent scope
- Model supplies: `queryText`, optional `focusNodeIds`, `relationshipPredicates`, `maxHits`, `includeMechanics`
- Tool result is structured JSON suitable for evidence presentation; Hermes must not claim hydrated mechanics when `hydration_status` is not `available`
- Register in `ORDERED_INTERACTION_TOOL_NAMES`; capability rule in `hermes_graph_plugin.py`

### 7G Persistence and replay

- SBW10a is a **derived read** — no new durable authority collection
- Same `(world_id, campaign_id, revision_pin, query_text, focus_node_ids, predicates)` ⇒ deterministic hit order and binding locators
- Graph head advance does not change pinned hydration; caller must supply new pin explicitly
- Safe to retry on unavailable DungeonMind or projection dependency failures
- No idempotency keys required (read-only)

### 7H Failure and HTTP behavior

| Condition | result_label | HTTP | Behavior |
| --- | --- | ---: | --- |
| Pin not found / world missing | `threat_query_hydration_not_found` | 404 | No hits |
| Projection/graph dependency down | `threat_query_hydration_unavailable` | 503 | No fabricated hits |
| Pin mismatch after projection | `threat_query_hydration_integrity_failure` | 500 | Fail closed |
| Malformed binding edges | per-binding `integrity_failure`; may aggregate | 200 with partial/integrity label | Threat identity preserved |
| DungeonMind unavailable | per-binding `unavailable` | 200 partial | Locators retained |
| Revision 404 | `exact_revision_missing` | 200 partial | No latest fallback |
| Digest mismatch | `integrity_failure` | 200 partial/integrity | Mechanics not trusted |
| Validation error | — | 422 | Pydantic detail |

Publication routes retain existing SBW09c2b label→status mapping; change only when existing labels cannot express §7A taxonomy.

## §8 Required implementation sequence

1. Re-anchor gate (§2) on `dd1a7f2a…` containing PR `#491` merge.
2. Add failing F1–F5 publication regression tests (red).
3. Repair admission classifiers F1 (green).
4. Repair retry authority F2 (green).
5. Repair committing replay F3 (green).
6. Repair connect-existing F4 (green).
7. Repair double receipt-save F5 (green); stop if schema gap blocks honesty.
8. Add SBW10a models with strict schemas (red tests for shape).
9. Implement `_collect_threat_hits` relationship semantics including `related_to_match` (red).
10. Implement binding enumeration + hydration service (red).
11. Expose `POST /api/live/threats/query-hydration` route + main registration.
12. Register Hermes `query_threat_mechanics_hydration` with scope inject.
13. Run full verification command matrix (§9); fix failures within allowlist.
14. Produce required handback (§12) before review request.

## §9 Verification ownership map

| Guarantee | Owning boundary | Command / scenario | Evidence |
| --- | --- | --- | --- |
| F1 admission 503/409/500 taxonomy | commit service | `test_admission_identity_*` | zero artifacts on failed admission |
| F2 retry terminalizes readable not_found | commit service | retry zero-match matrix | uncommitted, not recovery_pending |
| F3 c2a after reconstruction OSError | commit service | `test_committing_reconstruction_oserror_still_runs_c2a` | c2a invoked |
| F4 rejects Threat node rewrite | commit service | connect-existing assertion tests | no merge |
| F5 durable double-save honesty | commit service | `test_double_receipt_save_failure_returns_durable_prior` | disk truth |
| Zero/one/many Threat hits | hydration service | `test_zero_one_many_bindings_no_first_win` | explicit lists |
| Empty matched_node_ids ⇒ zero hits | hydration service | `test_zero_direct_matches_returns_empty_not_all_threats` | no all-Threat fallback |
| Relationship discovery | hydration service | `test_relationship_discovery_from_matched_non_threat_location` | `related_to_match:` reason |
| Exact revision hydration | hydration service + client | digest mismatch / 404 tests | no latest |
| Hermes tool scoped | interaction tools | `test_query_threat_mechanics_hydration_tool_is_registered_and_scoped` | inject proof |
| No durable writes on read path | hydration service | `test_no_durable_writes` | filesystem unchanged |
| Prohibited substitutes absent | repo search | §10 search commands | no matches in allowlist |

### Required commands

```bash
uv run pytest tests/test_threat_publication_commits.py tests/test_threat_publication_commit_api.py -q

uv run pytest tests/test_threat_query_hydration.py tests/test_threat_query_hydration_api.py -q

uv run pytest tests/test_hermes_graph_agent.py tests/test_live_query_hermes_graph.py \
  tests/test_hermes_graph_agent_host.py -q -k "hydration or threat_query"

uv run pytest tests/test_threat_publication_proposals.py tests/test_threat_publication_proposal_api.py -q

git diff --check
git diff --stat dd1a7f2a2783e2a2fb189150bd837065122bee8f...HEAD -- \
  apps/live_control_server/services/threat_publication_commits.py \
  apps/live_control_server/models/threat_query_hydration.py \
  apps/live_control_server/services/threat_query_hydration.py \
  apps/live_control_server/routes/threat_query_hydration.py
```

### Minimal live proof

1. From a published Threat at a known `revision_pin`, POST query-hydration with exact name → receive one hit with binding locators and hydrated mechanics.
2. Repeat with relationship-only anchor (location node) → Threat hit with `related_to_match:<node_id>:<predicate>`.
3. Query with text that matches no nodes and empty focus → zero hits (confirm not all Threats returned).
4. Stop DungeonMind → Threat/locator preserved; mechanics `unavailable`.
5. Hermes turn with fortification/siege-style query → tool event shows scoped pin and explicit hit count.

## §10 Adversarial test inventory

### Publication hardening

- Admission with identity storage unavailable → 503, no ledger artifacts
- Admission with `publication_identity_not_found` → 409, no artifacts
- Admission integrity failure → 500, no artifacts
- Retry after c2a zero match + not_found → uncommitted, not recovery_pending
- Committing replay reconstruction OSError → c2a still runs
- Connect-existing Threat `assertion_kind="node"` → rejected
- Double receipt-save failure → last durable disk record returned

### SBW10a query/hydration

- Duplicate labels → distinct Threat IDs (no collapse)
- Alias hit preserves canonical node ID
- Zero/one/many bindings without first-win
- Two Threats share exact mechanics but distinct identity
- Graph head advance with same pin → stable hydration chain
- Projection unavailable → 503
- Server unavailable → locators preserved
- Exact revision missing → no latest fallback
- Definition digest mismatch → integrity
- Wrong statblock ID in response → integrity
- Malformed `uses_statblock` edge → integrity not silent drop
- Wrong edge direction → integrity
- Client construction failure → bindings unavailable, not fake hydration
- Empty query does not construct DungeonMind client unnecessarily

### Prohibited substitutes search

```bash
rg -n "latest_revision|get_latest|current_head|corpus_path|label_match|first_match" \
  apps/live_control_server/services/threat_query_hydration.py \
  apps/live_control_server/services/hermes_graph_interaction_tools.py

rg -n "uses_statblock" apps/live_control_server/services/threat_query_hydration.py \
  | rg -v "enumerate|integrity|hydration"
```

Fail the PR if allowlisted paths introduce latest/label/corpus resolution or first-win binding selection.

## §11 Demolition declaration

```text
Replaced path: none in SBW10a (no duplicate backend/Hermes query hydrator discovered that used latest/label/corpus)
Deleted in this PR: no
If no, retained reason: no legacy exact-Threat hydration consumer found under Hermes/backend allowlist
Named remaining consumer: legacy StatblockViewModule / visual consumers remain for SBW10b demolition
Required deletion owner: SBW10b
```

## §12 Required handback

The implementation PR body and merge comment must include:

- [ ] Exact base `dd1a7f2a…` and actual head SHA
- [ ] Predecessor merge `601326b0` / PR `#491` cited
- [ ] Complete allowlist diff stat (every touched path named)
- [ ] F1–F5 test command output pasted or linked
- [ ] SBW10a test command output pasted or linked
- [ ] Hermes tool registration proof (test name or trace excerpt)
- [ ] Prohibited-substitute search results (§10)
- [ ] Minimal live proof notes with exact `revision_pin`, Threat node ID, binding triple
- [ ] Demolition ledger (§11)
- [ ] Bounded discovery paths with necessity one-liners
- [ ] Explicit confirmation: no Threat Sheet, edit, embed, placement, combat, or media shipped
- [ ] Review cycle 1 repair notes if PR `#502` requested changes

## §13 Acceptance rubric

### Publication hardening

- [ ] Unavailable identity/publication dependencies map to 503 with zero commit artifacts on failed admission
- [ ] `publication_identity_not_found` and stable stale op map to 409/uncommitted — not transient recovery
- [ ] Committing replay runs c2a after reconstruction OSError
- [ ] Connect-existing rejects Threat `node` assertion rewrites
- [ ] Double receipt-save returns durable disk truth without synthetic counters
- [ ] No publication regression in proposal/identity suites

### SBW10a query/hydration

- [ ] `revision_pin` required on every query; no current-head default
- [ ] Zero/one/many Threat hits explicit
- [ ] `matched_node_ids is empty` with no focus ⇒ zero hits, not all Threats
- [ ] Relationship hits use `related_to_match:<node_id>:<predicate>`
- [ ] Every `uses_statblock` edge enumerated per Threat
- [ ] Hydration uses exact revision client only; digest equality gates trust
- [ ] Server unavailable preserves Threat/locator honesty
- [ ] Hermes tool read-only with injected scope
- [ ] No latest, label, corpus, or first-win paths in allowlist
- [ ] No mechanics copied into graph storage

## §14 Reviewer protocol

1. Verify HEAD ancestry includes `601326b0` and branch recorded base `dd1a7f2a…`.
2. Trace F1 fix: admission must call shared classifiers — read `_admit_and_build_record` and route mapping.
3. Trace F2: search `publication_identity_not_found` in retry path — must not become recovery_pending after readable zero-match.
4. Trace F3: reconstruction exception path must still invoke c2a lookup.
5. Trace F4: connect-existing assertion validation includes Threat `node` rejection.
6. Trace F5: second save failure returns prior durable record; confirm no synthetic merge count.
7. Open `threat_query_hydration.py` — confirm `_collect_threat_hits` relationship walk and empty-match rule.
8. Confirm route rejects missing `revision_pin` (422).
9. Run §9 commands locally; spot-check Hermes test.
10. Execute §10 prohibited-substitute search.
11. Confirm allowlist-only diff; no prompt/eval/UI scope creep.

## §15 Re-review protocol

After each fix pass on PR `#502`:

1. Re-run full §9 publication + hydration + Hermes command set.
2. Re-run §10 prohibited-substitute search on touched paths only.
3. Re-verify relationship semantics tests (`related_to_match`, empty `matched_node_ids`).
4. Re-verify F1–F5 regression tests individually if fix touched adjacent code.
5. Confirm no new durable write paths introduced in hydration/Hermes layers.
6. Update handback checklist (§12) with new command output and changed paths.

## §16 Stop conditions

Stop and report (do not expand scope) if:

- Implementation base does not contain merged PR `#491` publication commit authority
- F5 honest replay requires a commit-record schema field that does not exist — report persistence schema gap instead of inventing counters
- Graph projection cannot expose `query_context.matched_node_ids`, match reasons, and relationship discovery at pinned revision
- Exact DungeonMind client lacks `get_exact_revision` or digest on response
- Hermes turn policy cannot supply authoritative `revision_pin`
- A required path falls outside §5 allowlist + bounded discovery budget
- Tests prove latest/label/corpus/first-win substitution would be required to pass
- Review asks for Threat Sheet UI, edit, embed, placement, or combat within this PR

## §17 Named successors and what remains false

| Successor | Remains false after this PR merges |
| --- | --- |
| `SBW10b` | Compact/full Threat Sheet UI; legacy `StatblockViewModule` demolition |
| `MAGIC-D3` | End-to-end dogfood: publish → query → hydrate → project |
| `SBW12` | Revision-pinned Plan embed |
| `SBW13` | Mechanics edit / append revision |
| `SBW14` | Governed binding preference / revision adoption |
| `AOW03`/`AOW04` | Durable object placement |
| `COMBAT01`/`SBW15` | Exact-revision combat adapter |
| `SBW16`–`SBW18` | Media generation/selection/3D recon |

Workbench publication confirmation UI, generic object publication, undo/retraction, and campaign-preferred latest mechanics policy also remain false.

## Final dispatch check

- [ ] Re-anchor gate passed against `dd1a7f2a2783e2a2fb189150bd837065122bee8f`
- [ ] Predecessor PR `#491` merge `601326b0` in history
- [ ] F1–F5 failing tests added before service fixes
- [ ] SBW10a models/routes/Hermes tool within §5 allowlist only
- [ ] Relationship semantics: `related_to_match` + empty `matched_node_ids` rule proven
- [ ] §9 commands green with pasted evidence
- [ ] §10 prohibited-substitute search clean on allowlist
- [ ] §11 demolition declaration included in handback
- [ ] §13 acceptance rubric satisfied or explicit waivers documented
- [ ] §16 stop conditions checked — no scope expansion
- [ ] Downstream successors (`SBW10b`, `MAGIC-D3`, placement, combat) remain explicitly false
