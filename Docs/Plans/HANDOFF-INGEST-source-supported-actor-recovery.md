# INGEST: recover a missing source-supported actor

Status: ACTIVE — bounded DOGFOOD implementation lease, activated by PRIME after
independent contract critique and the concrete retained read-only proposal.
No provider call, retained correction or publication is authorized.
Base: Buddy main b73b3f6225aaed4954a86a54005c6837eeaa49e9.
Proposed branch: codex/ingest-source-actor-recovery, existing suitable checkout only.
Topology: serial successor to settled #1403; independent of the separately pinned
read-only Session29 review preparation at12bf3076e.

## Outcome and critique

Recover ONE explicitly named actor omitted from an immutable recap candidate,
without merging or renaming another actor. A source-bound held child can introduce
a local character and repair only its declared affected assertions atomically.
Existing V1–V10 operations cannot create an NPC. PC references and node renaming
must not be repurposed. An omission-only child is containment, not full recovery.

This does not solve unavailable transfer predicates. In the motivating private
case, distinct donor and captain identities must remain distinct, but a gift
must not become current possession. Unsupported assertions remain explicitly
unresolved; no label can smuggle an unadmitted predicate into the graph. Full
Session29 semantic acceptance remains open until its retained proposal resolves
these representation choices.

## Proposed bounded contract

- New versioned request/manifest/operation basis, with explicit closed mapping
  into the existing source-bound child envelope. Preserve all V1–V10 meanings,
  rows, hashes and replay. Review the exact new discriminator/basis design before
  activation; do not infer that response create_new_node_count permits insertion.
- Exact parent run/revision, candidate/source/span/profile pins and current frozen
  World authority. Same under-lock fresh parent/resolver/source validation as1403.
- One character introduction: exact literal name, verified source span and
  codepoint range/quote, concise source-grounded description. No caller nativeID,
  corpus reference, inferred surname/title/species/kinship, or authority flags.
  Host derives evidence, reserved deterministic localID and fixed held/private/
  source-derived candidate state. Reject collision/ambiguous name or mention;
  never merge an existing character by similarity.
- At most FOUR affected existing edges total. Each is either an endpoint retarget
  to the introduced actor OR an explicit omission, with disjoint targets. Require
  whole old tuple, complete evidence preimage/record hash and declared endpoint.
  Retarget preserves the other endpoint/predicate/evidence; source and existing
  native domain/range qualification must support the resulting assertion.
  No arbitrary edge creation, label rewrite, new predicate or implicit cascade.
  Omitting unsupported affected claims is explicit and not reported as recovered.
- Host validates the source actor/affected assertions as a proposed operator edit;
  literal quote matching is not a claim of automated entailment certification.
- Addition and declared assertion changes replay atomically: any invalid preimage,
  missing source, bad predicate, duplicate target, native-looking supplied ID or
  foreign evidence leaves no child row/package. Retain parent and source bytes.
  Preserve V12 package binding, no-follow/nonblocking reads, exact retry and
  crash resume, legacy collision behavior and inherited PC lineage.
- Held candidate only. No semantic acceptance, canonical World identity binding,
  Graph object creation, prepare/confirm or publication. Current reader should
  expose the new candidate through its existing list/chip/evidence contract.

## Exact implementation write lease

- This handoff (activation and actual predecessor settlement only).
- apps/live_control_server/models/extract_promote.py
- apps/live_control_server/routes/extract_promote.py (existing endpoint union only)
- apps/live_control_server/services/recap_semantic_candidate_correction.py
- apps/live_control_server/services/recap_semantic_disposition.py
- apps/live_control_server/services/extract_promote.py (existing consumer dispatch)
- src/application_state/ingest/service.py (closed basis/mapping validation)
- tests/test_recap_semantic_candidate_correction.py
- tests/test_recap_semantic_disposition.py
- tests/integration/test_recap_evidence_append.py
- tests/test_extract_promote_managed_world_target.py

No migrations, source registry, shared graph vocabulary, provider/GenerationEngine,
roster matcher, kernel, gold, source bytes, UI or other paths. Rebrief before any
necessary expansion. No new checkout, environment, preview or /tmp task directory.

## Required owning proof

Actual synthetic production extraction omits an explicitly named actor and has
wrong-actor assertions. Real APP-STATE held child introduces that actor and repairs
only declared supported endpoints/omissions; existing captain/PC/source identities
unchanged. Reopen, source-bound assessment, exact same-request retry and crash
recovery must reproduce exact child/manifest. Negative cases cover ambiguous name,
missing/foreign quote, Unicode/CRLF offsets, stale parent/record/evidence, rejected
or superseded lock-wait parent, unsupported predicate, unrelated edge, duplicate
ID/target, native-ID injection and legacy collisions. Old V1–V10 replay stays
unchanged. Candidate reader counts/evidence remain truthful.

Only unique disposable54329 test databases, when PRIME confirms fixture available.
No retained54330/54331 or private source/provider tests during implementation.
Implement→test→cumulative diff→commit/push/one PR→ARCHITECTURE exact-head review→
PRIME guarded merge/adoption. Retained apply needs a separately pinned concrete
proposal and operational authority; this design supplies neither.

## Activation gates — satisfied as recorded below

1. DOGFOOD exact retained read-only proposal confirms actor/affected edge scope
   and separates supported retargets from missing transfer representation.
2. ARCHITECTURE critiques this bounded contract, including atomic omission scope,
   exact discriminator/basis placement and old-source-bound replay compatibility.
3. PRIME pins exact request fields/version/basis mapping, source-grounding and
   uniqueness rules, final write lease, test commands, owner/checkout/fixture.

## PRIME request and replay contract for final critique

This section pins the accepted discriminator/source-preimage design. Implementation
is activated only within the owner/path/test boundaries below. Retained apply
remains separately held.

### Exact version mapping

Use request/response schema `dmb_recap_candidate_correction_request_v11` /
`dmb_recap_candidate_correction_response_v11`, operation derivation
`operator_recap_semantic_candidate_correction_v11`, and manifest schema
`dmb_recap_semantic_candidate_manifest_v11`. Add inner `RecapSemanticBasisV13`
with schema `dmb_recap_semantic_basis_v13`, the same exact-revision/inherited-PC
proof fields as V11, and the new operation derivation/manifest literals.
V12 is already the source-binding envelope: preserve its schema and outer
`operator_recap_semantic_source_binding_v11` meaning. Add the ONE explicit closed
mapping request 11 -> correction_v11 / manifest_v11 / inner BasisV13. Do not
renumber any existing basis or infer mappings by numeric proximity.

The V11 request has only these top-level fields (extra fields forbidden): `schema`,
`parent_run_id`, strict integer `expected_parent_revision`,
`parent_candidate_sha256`, `source_revision_sha256`, `span_index_sha256`,
`profile_id` fixed to `recap_category_v1@1.0`, `misbound_actor_id`,
`actor_introduction`, and `affected_edges` (0..4). Every digest is lowercase SHA256.
The manifest retains the complete validated request and the host-derived new node
and exact before/after edge records, in deterministic target-ID order. Reuse the
existing canonical JSON and source-bound child UUID derivation; the manifest's new
schema separates this operation from every older request. All V1–V10 bytes,
hashes, child IDs and replay results must remain unchanged.

### Actor grounding and identity

`actor_introduction` fields are `literal_name` (1..160 codepoints),
`source_span_ref_id`, `name_start`, `name_end` (strict zero-based codepoint offsets,
half-open in the whole frozen source), `replacement_description` (1..4096), and
`description_anchor_quotes` (1..4 distinct exact nonblank quotes, each <=4096).
The name range must be wholly within the referenced indexed span, exactly equal
the supplied literal, and not embedded in a longer letter/number/underscore name.
Description anchors must occur in that same frozen span. Description support is
an explicit operator judgment bound to these quotes; literal matching alone is
not semantic certification. No inferred surname, aliases or native identity.

Offsets use UTF-8 decoded source with newline translation disabled: CRLF occupies
two codepoints; no NFC/case/newline normalization for evidence or hashing. For the
name ambiguity check only, compare NFC+casefold+trimmed display names and aliases
against all existing actor nodes: any match rejects for explicit identity review.
An invalid Unicode range or partial embedded name rejects. Host derives one local
ID `node:recovered-actor:` plus SHA256 of canonical JSON containing parent run ID,
parent candidate SHA, source revision SHA, span ID, name range and literal name.
Any collision with ANY candidate node/edge/Beat ID rejects, never adopts or merges.
No caller ID or corpus reference is accepted. Host emits the normal candidate
character shape, only the literal display name, corpus_ref=null, source-derived
frozen evidence, and existing held/private defaults. Existing actors are immutable.

### Mechanically affected assertions only

Each `affected_edges` entry has `action` (`retarget` or `omit`), `edge_id`,
`expected_edge_sha256` (whole record, existing canonical encoding),
`expected_evidence_refs_sha256`, `original_from_id`, `original_to_id`,
`original_predicate`, `misbound_endpoint` (`from_id` or `to_id`),
`source_span_ref_id`, and `actor_anchor_quotes` (1..4 exact quotes). No new endpoint
or predicate field: retarget always replaces ONLY the declared endpoint with the
host-derived actor ID. Both preimage hashes and old tuple must match; the declared
old endpoint must equal top-level misbound_actor_id. Reject missing actor, self-
replacement, duplicates, unrelated edge cleanup, or a source_span_ref_id not already present in
that edge's frozen evidence. Each affected edge must cite the actor-introduction
span. The actor_anchor_quotes are additional VALIDATION-ONLY exact literal context
from that same raw span and must contain the exact recovered name; they need not
be members of the old anchor_quotes array. They never append or rewrite the edge's
evidence. Bind these validation anchors in the operation manifest and its basis,
while preserving the complete old edge/evidence hash preimages. This is
bounded operator review of an affected assertion, not automated entailment.

Retarget keeps other endpoint, predicate, label, description and evidence bytes.
The retained proposal must establish that the unchanged label and tuple express
one supported assertion; a gift label under possession, or a label naming the old
actor, cannot be repaired by endpoint substitution and must reject or be omitted.
Native endpoint/predicate qualification remains mandatory. Omission withdraws only
that exact misbound assertion; it cannot clean unrelated semantic issues. No Brin
interaction repair or other neighboring edits fit this operation. The result must
report introduced=1, retargeted=N, omitted=M, and unresolved gift/interaction gaps
separately. Withdrawal of every supply assertion is partial actor recovery and
false-claim containment, never faithful gift reconstruction or full acceptance.

### Consumer and test gates

Explicitly inspect/update each owning consumer as needed inside the proposed paths:
request union, is_recap_correction, source-bound assessment, child replay,
APP-STATE inner dispatch, inherited-PC ancestry, exact review projection and
reviewed-effect digest/prepare/confirm handling. Candidate introduction conveys
no native identity and no new publication authority. Compatibility tests must
prove it is still inspectable as a candidate and cannot bypass existing identity,
source or semantic holds. No UI lease is needed for that read-model proof.

Owning verification command, after PRIME confirms disposable 54329 available:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. TMPDIR="$PWD/.pytest_cache" <existing-runtime-python> -m pytest -o addopts='' --basetemp=.pytest_cache/actor-recovery tests/test_recap_semantic_candidate_correction.py tests/test_recap_semantic_disposition.py tests/integration/test_recap_evidence_append.py tests/test_extract_promote_managed_world_target.py -q --tb=short`.
The admin DSN must target only the confirmed disposable fixture and must not be
printed. Use shared dependencies; no installs or other runtime targets. Run Ruff
on changed Python paths and cumulative `git diff --check`.

The actual production-producer fixture must prove new local actor + exact supported
retarget/omission, unchanged captain and every unaffected node/edge/Beat/source
byte, fresh DB reopen/replay/assessment/retry, crash-resume and mixed old/new PC
ancestry. Exercise every rejection before child/package claim, including lock-wait
authority drift. The public handoff/tests must contain synthetic material only.

## Activation and concrete scope — PRIME

Independent Architecture critique of exact 15becfb3a56762c82c53584883e12c2b4aecb9d6
accepted the contract and eleven paths subject to the validation-only anchor
clarification now incorporated above. DOGFOOD's private read-only proposal is
`session29-correction-review-20261017.md` in the established private experiment
location. It confirms the distinct omitted actor and three misbound assertions;
all three action-label/predicate combinations require withdrawal in this slice.
Zero retargets is expected for that retained example. Recipient inventory rewrite,
Brin interaction, separate item counts and faithful giver/action semantics remain
open, outside this slice, and cannot be claimed completed by actor recovery.
No retained correction is approved by the implementation lease.

Owner: DOGFOOD, existing checkout
`/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`.
This handoff is on `codex/ingest-source-actor-recovery` in PRIME's checkout. Create
a distinct branch `codex/ingest-source-actor-recovery-implementation` from
fetched main b73b3f6 in DOGFOOD's existing checkout and carry only this handoff.
No concurrent edits by PRIME to the eleven leased paths after dispatch.
The proposed eleven-path set above is now the exact active write lease; all other
prohibitions remain. Old source-binding implementation lease is closed by merge
b73b3f6; its historical docs are not an additional implementation write path here.

Disposable fixture: PRIME verified the owned container
`dungeonbuddy-review-fixture-pg` at ID
`3c1a9eadadb2ed8a370d7008037c5bba95d83fd84c9b44b7070714710ccfc5a3`
running with no TCP clients on54329 at activation. DOGFOOD's prior fixture work and
Architecture's prior consumer are finished. It is reserved for this slice's unique
throwaway test databases; PRIME retains lifecycle/cleanup responsibility. Existing
runtime Python is
`/home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/runtime/bin/python`.
Return at a concrete unexpected boundary/required path expansion, or deliver one
implementation PR with exact cumulative diff and owning evidence. Architecture
reviews exact head; PRIME merges/adopts when gates pass. No additional operator
confirmation is required for the bounded implementation or independent review.
