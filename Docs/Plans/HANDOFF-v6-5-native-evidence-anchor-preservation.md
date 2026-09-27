# HANDOFF — V6.5: Buddy native evidence/anchor preservation and V6 exit receipt

**Created:** 2026-09-27
**Status:** ACTIVE — activated 2026-09-27 after MIND/Buddy predecessor sync
**Owner/repository:** DungeonMindBuddy; MIND receives the V6 exit evidence, DEMO coordinates Buddy leases
**Design base:** Buddy `2ccc96ff2a7d76328578609d5289fd3babcf6442`
**Activation base:** Buddy `d5f0ada66ddbebf2ec1dca55ea493ff21da476c3`
**DungeonMind main:** `0ab1ae0133ca9038a1d82eb488ed805f09e49feb`
**WorldKeeper main:** `662a028fb1882719c4c3e192134a1a6b7a58026c`
**Installed DungeonMind pin:** `0f709d76fdc53bac9c9258d1751463ae2c76ca71`
**Installed WorldKeeper pin:** `49a8620f066ce7ef8972a699020c012f50af9158`
**PR topology:** parallel-independent; one assigned hermetic V6 preservation proof PR
**Implementation base:** Buddy `d5f0ada66ddbebf2ec1dca55ea493ff21da476c3`
**Suggested branch/title:** `codex/v6-5-evidence-anchor-preservation` / `VNEXT: prove Buddy evidence and anchor preservation`

This ACTIVE handoff authorizes exactly one hermetic proof lane under the two-path
write lease in §4. It authorizes no runtime mutation, V7 dispatch or production
switch.

## 1. Exit ruling and accepted predecessors

DungeonMind's roadmap V6 asks for preservation of world-global knowledge,
campaign-specific knowledge, cross-campaign reads, GM visibility, player
fail-closed visibility, session focus, fictional-time metadata, and complete
object/evidence/anchors through Buddy's domain contract.

- V6.0.1 / Buddy #747: merge `99b8d431d6558f4d6028c736d41ebaa97af84ca5`;
  corrected domain/source/evidence metadata contract.
- V6.1 / #749: head `9e2abbae42acc847b214460644caef2448637495`, review
  `5312320001`, merge `7a63c8b39937776ddede24d3d76001ef59fd37c4`;
  production Buddy request/context mapper and domain policy, with role/scope/focus tests.
- V6.2 / #767: head `69fedb9918c602a92af32d74453a2b00ed2b73da`, review
  `5324647959`, merge `f30b4c906bb179b25f00207c40cb38c0debdc264`;
  dormant complete-object DTO, temporal and evidence metadata preservation.
- PLAY-1 / #773: head `5a1736c55988e4b852bbcc2f0ada36d493fa5668`, review
  `5327172769`, merge `7fe771e86df2e796484b058aa2e6a8e7c94c9fb9`;
  in-memory Buddy → WorldKeeper governed consumer composition.
- PLAY-2 / #779: head `2d5ab6ade1d89ec608c941093819ea36404fd18e`, PRIME
  review `5331441470` (Cycle 2), merge
  `2ccc96ff2a7d76328578609d5289fd3babcf6442`; four isolated PostgreSQL
  witnesses, zero skips, plus 54 PLAY-1/V6.2 regressions in independent review.
  This proves publication/replay/restart/concurrency/integrity, not source admission.

V6 is not yet certified complete. No accepted Buddy test consumes native
`EvidenceReadService.get_assertion_evidence`, `get_evidence` and
`resolve_source_anchor` through its actual domain context. V6.2 deliberately
stopped at source bindings and deferred body/span hydration. The generic V4.2
API already exists in the installed DungeonMind package, so the next work is
an acceptance proof using existing runtime capability.

V6 source-anchor proof means the accepted V4.2 navigation metadata, context-bound
identity and revalidation contract. It does not mean opening a source body or
inventing a product highlight. Physical source hydration, browser wiring and
production cutover are later consumer obligations. No generic Kernel prerequisite
has been identified; stop and route a defect if this proof discovers one.

## 2. One merge-ready invariant

Using the real V6.1 Buddy mapper/context and existing native DungeonMind read
services, the canonical Buddy preservation fixture yields exactly the admitted
complete-object/evidence/source-anchor identities and metadata. Hidden or
out-of-scope support cannot be recovered through a direct evidence ID or anchor.
Fresh source/authority changes invalidate old anchors without corrupting the
coherence of an already constructed read context.

The reviewed report joins this new evidence to the accepted V6.1/V6.2 and
PLAY-1/PLAY-2 results and accounts explicitly for every V6 exit requirement.
Green helper tests alone do not confer V6 acceptance. MIND records the V6 exit
judgment only after independent review and accepted merge of the proof.

## 3. Implementation and evidence contract

Reuse `tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json`,
`build_dungeonbuddy_read_context`, and the V6.2 complete-object adapter.
Construct real `ParsedKnowledgeRevision` and `InMemoryKnowledgeSourceReader`
objects as the accepted tests do. Do not substitute a fake Buddy domain policy,
return canned read results, or copy Kernel admission logic.

Add synthetic in-test variants to the existing fixture rather than rewriting
its accepted bytes. Explicitly create evidence supported only by a GM-only
assertion when testing denial: the base fixture's shared evidence may still be
legitimately visible through a public supporter.

Required cases:

1. Exact assertion-evidence lookup, exact evidence lookup and anchor resolution
   preserve evidence/artifact/revision IDs, digest, locator, navigation flags,
   explicit span reference when present, admitted supporter IDs and completeness.
   Preserve a missing span ID; never derive it from `paragraph:14` or elevate
   `can_highlight_span` into proof that source text was opened.
2. Join a selected object's returned evidence IDs to native evidence/anchor reads
   under the same Buddy role/scope/revision, with coherent source-reader state.
   Assert complete-object temporal metadata and source classification/context
   remain unchanged. No legacy World read service or full-graph reconstruction.
3. World-global and campaign A knowledge remain admitted in campaign A; campaign
   B-only support is excluded there and admitted through world wildcard scope.
   Exact evidence IDs cannot bypass this boundary. Include GM and player cases.
4. Player cannot recover GM-only, provisional or retracted supporting assertions.
   Denied evidence/anchor results contain no hidden source metadata, locator or
   support IDs. Shared evidence remains available only through admitted support.
5. Repeated same-context anchor creation/resolution is deterministic. Forged,
   malformed, foreign-space, changed-revision and changed-role/context tokens
   fail closed. Rebuild an otherwise equivalent context and check exact results.
6. Session focus does not change admitted assertion/evidence membership or
   fictional-time meaning. Anchor tokens bind the full request, including focus:
   a changed-focus request may need a fresh token; do not require cross-context
   token identity in the name of semantic parity.
7. Mutate a controlled source reader after creating a context. The existing
   pinned context remains coherent; a fresh context rejects an old anchor after
   source lifecycle/visibility/revision-digest or evidence-locator drift. Cover
   missing source/revision and source-revision/artifact mismatch as well.
8. Audit native serving/materialization/publication paths used by this proof and
   the accepted write proof for product-specific semantic dependencies. The
   native path must not execute legacy GM/PLAYER/campaign/NPC/fictional-time
   policy or import a Buddy/D&D implementation to decide generic admission.
   Record the exact modules/entry points examined. Existing historical readers
   and compatibility exports remain governed by V1/V10; do not require their
   premature deletion or treat mere historical vocabulary in the repo as a
   native-runtime failure. Any actual dependency discovered is a stop to MIND.

The report names each V6 requirement, its owning production entry point, exact
test, fixture/descriptor identities, expected/observed result, and limitation.
It records accepted PLAY-2 evidence by merge/review rather than claiming this
in-memory preservation test repeats PostgreSQL durability. Keep the base profile
`dungeonbuddy.dnd5e` revision 1 distinct from PLAY-1/2's opt-in revision 2 V3
custom-predicate profile; no profile transition is implied.

## 4. Expected write lease after activation

```text
tests/test_v6_5_evidence_anchor_preservation.py                  # new
Docs/Reports/REPORT-v6-preservation-acceptance.md                # new
```

No production edits, new API, migration, fixture rewrite, package pin, lockfile,
database, source-body reader or frontend change is expected. If needed to expose
a defect, keep the failing witness within this test file and return it to the
owning steward instead of expanding the proof into a repair PR.

Predecessor state sync belongs to the stewards before dispatch:

- MIND: `Docs/Handoffs/HANDOFF-STEWARDSHIP-vnext-roadmap.md` and
  `Docs/Roadmaps/ROADMAP.md`. Record current #79 anchor, #78 V3 finalization,
  V6.0.1/V6.1/V6.2/PLAY-1/PLAY-2 accepted facts and this remaining V6 proof.
  Keep V6 open and V7 undispatched. This is control-plane correction, not runtime.
- Buddy: settle PLAY-2 status in its handoff, evidence report and the DEMO
  roadmap plus its active mirror if they still claim ACTIVE/HOLD or an
  unauthorized token after merge. Preserve original implementation evidence;
  append accurate reviewed/merged acceptance and its scope. These files are not
  leased to this worker. The designing stewards settle them under their authority.

No DungeonMind architecture/contract/schema changes are required for that sync.
No WorldKeeper runtime or roadmap capability is added. The independent Buddy
first-World endpoint repair at `6e5bd19c68a0b8bbe2657f2d0e60c9f3df95fba2`
remains a DEMO product repair; it is not a Kernel or V6 prerequisite.

## 5. Activation and isolation

The activation gates are satisfied. MIND PR #80 merged at
`0ab1ae0133ca9038a1d82eb488ed805f09e49feb` after PRIME PASS on reviewed head
`f4bb49cad88847877fc0e6862b72f8066bcde69f`. Buddy's PLAY-2 predecessor sync
landed on main at `10a7b42da2c028889acbf085a577844252bc7f79` and records
#779 as accepted/merged. DEMO then rebriefed its disjoint world-scope Plan-read
lease at `bf67c16fceba09026cef7a6e833a58666fa5855a` and clarified selected-object
world scope at `d5f0ada66ddbebf2ec1dca55ea493ff21da476c3` before this branch dispatched.

A clean `uv sync --locked` at activation installed DungeonMind
`0f709d76fdc53bac9c9258d1751463ae2c76ca71`, WorldKeeper
`49a8620f066ce7ef8972a699020c012f50af9158`, and GenerationEngine
`9122257f5a8842e4771990a3316130bc1bf7e332`.

Open PRs #763/#764/#765 are the stacked Rules sequence; #760/#761 are stacked UI
design work. None leases the two §4 paths or shares runtime state with this
proof. DEMO's active Plan-read work and blocked first-World edge repair remain
separately serialized by DEMO. V6.5 is explicitly parallel-independent of those
lanes: it uses only a new test, a new report, an in-memory source reader, and no
database/network/provider/server/port.

No successor branch/PR may be opened by the worker. Any discovered production
defect or required path outside §4 stops this lane and returns to the steward.

The new proof is hermetic: in-memory source reader, synthetic variants and no
network/provider/database/server/port use. Existing PLAY-2 acceptance is inherited
at its exact reviewed merge; repeating its DB test is not required unless a
dependency/runtime change makes that evidence stale. Such a change is outside
this lease and requires re-anchor before proceeding.

## 6. Verification and handback

```bash
uv sync --locked
uv run pytest -q tests/test_v6_5_evidence_anchor_preservation.py
uv run pytest -q tests/test_v6_0_1_dungeonbuddy_evidence_metadata_contract.py tests/test_v6_1_dungeonbuddy_vnext_domain_runtime.py tests/test_v6_2_vnext_complete_object_adapter.py tests/test_con_ready_play_worldkeeper_consumer.py
uv run ruff check tests/test_v6_5_evidence_anchor_preservation.py
git diff --check
```

New required witnesses must have zero skips. Record installed `direct_url.json`
pins and canonical fixture/domain/profile digests, without changing historical
acceptance artifacts. Classify any focused regression against the actual base;
the known eight default-suite collection errors are not a green full suite or
automatic permission for unrelated fixes. The design author has inspected
existing tests/contracts but has not executed or claimed this new proof.

Handback includes exact design ref/base/head/PR, cumulative changed paths,
commands/results, complete V6 requirement-to-evidence mapping, negative and
source-drift results, native boundary audit, inherited PLAY-2 review/merge,
remaining limitations, and a proposed V6 exit judgment. A failure, skipped
required witness, dependency mismatch or unresolved preservation row is HOLD.

After independent review and authorized merge, MIND may record
`V6_DUNGEONBUDDY_PRESERVATION_ACCEPTED` only when every V6 row is accounted for.
The next action is then to design the first bounded V7 bridge-genesis slice
against the accepted state. This handoff authorizes no migration manifest,
legacy freeze, genesis publication, production switch or automatic V7 dispatch.
