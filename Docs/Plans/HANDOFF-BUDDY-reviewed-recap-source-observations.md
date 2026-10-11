# HANDOFF — BUDDY reviewed recap source observations

**Status:** DESIGN REVIEW / BLOCKED implementation — Root review of this exact branch/commit and recorded activation required before implementation.
**Owner:** Buddy producer and review orchestration; DungeonMind owns finalized review materialization and the existing observation read facet.
**PR topology:** serial. One assigned Buddy implementation PR; no companion Core PR.
**Design base:** Buddy `78b0ab1236303577c8dfaf283ca59be47b09f4bc` (#1073); Core pin `ba6069b91e1a608f125548860502a69b4c3e3fc6`.
**Design PR title:** `BUDDY: define reviewed recap source observations`
**Implementation PR title after activation:** `BUDDY: propose reviewed recap source observations`
**Design authority exception:** PRIME explicitly authorized this single design PR on 2026-10-11. A reviewed, pushed branch pinned by Root is sufficient contract authority for activation; merge onto main is not an extra activation gate for this slice.

## 1. Question and invariant

Can a reviewed recap description reach the ordinary selected-World Agent as a separately selected source observation, while preserving the object's authored summary and the exact source, identity and review authority?

For an eligible recap node description, Buddy proposes an independent `attribute` assertion with the same resolved subject and verified source evidence. Its text is visible for semantic review and is not selected by default. A finalized review selecting that assertion publishes it through the existing Core boundary. Core complete-object retrieval and Buddy's ordinary object-expansion consumer then expose the description with its review/publication/source/span provenance. The canonical object summary remains unchanged.

Identity acceptance and description acceptance are separate decisions. Selecting a node does not select or approve its description; selecting a description cannot implicitly create or bind its subject.

## 2. Observed defect and authority

The C2S1 publication at `rev:63513018ac05c26bc623fb3dfa324876` created four source-local objects. Their object summaries are null; rich descriptions remain inside reviewed node assertion values but are absent from Core's `reviewed_source_observations` and Buddy's consumer facet. The existing relationship and source anchors read successfully, and all 14 requested quotes were found in the actually opened sources.

Private witness: `/home/drakosfire/.local/state/dungeonmindbuddy/recovery/c2s1-current-parent-20261011/consumer-witness.json`, SHA-256 `bec6dc3957cb4baaed3f6d7418e019625d5ac635fa9148434430cc3068d3f2a3`. This proves a description-consumer gap, not a semantic quality score or an Agent answer.

Core `world_graph_retrieval._observation_value` accepts an accepted ATTRIBUTE with `value.property_term == "session_observation"`, nonempty `value.summary` and `value.kind`, and no Core predicate. Its reader additionally checks finalized review/publication lineage, subject presence, campaign/visibility, source revision and support evidence. Buddy already expresses this shape in `map_connect_existing_support_assertions`; `_qualified_assertion_update` translates Buddy's predicate into `value.property_term` and clears the Core predicate.

Use that exact existing term. The eligible Core shape is `assertion_kind="attribute"`, `acceptance_state="accepted"`, an active exact `subject_object_id`, `predicate=None`, and a JSON object value containing `property_term="session_observation"`, nonblank `summary` and nonblank `kind`. Source artifact/revision and support EvidenceRefs must agree with the finalized review and selected campaign/visibility. The Buddy precursor may use predicate `session_observation` only because its existing adapter moves it into `value.property_term` and clears the Core predicate. Do not introduce a new vocabulary term or a `dnd5e:` predicate for this attribute. The observation is a source-specific reviewed statement, not an authored summary or relationship.

## 3. Bounded producer behavior

Eligible inputs are typed, integrity-validated recap `source_extraction` candidates with a nonblank description, verified single source artifact/revision, valid evidence spans/quotes and a resolved mutating identity. Retained `dmb_candidate_graph_preview_v0` / `0.1` candidates qualify through those same checks. Their historical structural acceptance supplies provenance, not automatic semantic approval. Blank descriptions produce no companion. Unresolved, deferred, rejected, collision-blocked, unverified or non-recap inputs produce no new companion through this slice.

Emit one distinct attribute proposal per eligible source-node description. Reuse the existing observation mapping and evidence construction; do not copy arbitrary persisted `node.value.summary` on the read side. Preserve the original description text subject to existing whitespace normalization, mapped kind, qualified/canonical subject, source artifact/revision, catalog URI, span evidence, campaign/session, visibility and epistemic classification. Do not strengthen speculation into fact or strip a source-session qualification. Any temporal field follows the existing typed contract; invent no new temporal encoding.

For create-new identities, propose the node and companion separately. The companion depends on the exact node assertion in that contribution slice. For explicitly verified existing identities, reuse the support-only path without emitting a duplicate companion or competing node. Existing authored summary, role, aliases and identity decisions retain their current protections.

The review projection must show the actual observation text and evidence, not only an object label. Mark source-description observations `selected_by_default=False`, including the reused existing-identity support path when it carries a description. PRIME or the independently assigned steward reviews source support, entity role, speculation, temporal meaning and dependencies under the existing delegated GM confirmation authority. No new blanket operator approval gate is added. Human identity decisions remain necessary only when the existing identity contract requires one, including the held Thrin ambiguity.

## 4. Expected write lease

Only after ACTIVE activation, expected production writes are:

- `src/graph_memory/candidate_graph_to_contribution.py` — bounded observation mapper reuse/refactor.
- `src/graph_memory/extract_identity_gate.py` — companion proposal and selected-attribute subject/dependency validation, including the existing multi-slice reconstruction.
- `src/graph_memory/extract_promote_review_projection.py` — observation text, explicit selection and slice-qualified dependency presentation.
- new `apps/live_control_server/services/recap_source_observation_prepare.py` — internal observations-only fresh-package preparation for exact already-published source-proven subjects, reusing the existing exact-object reference and contribution/review primitives.
- `src/graph_memory/extract_promote_proposal.py` — seal and validate the source-proven existing-subject binding in the existing package effect.
- `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py` — confirm-time reproof of that binding before existing guarded review publication.

Expected tests:

- `tests/test_candidate_graph_to_contribution.py`
- new `tests/test_recap_source_observation_producer.py`
- new `tests/test_recap_source_observation_followup.py`
- `tests/test_reviewed_extract_confirmation.py` only for owning prepare/confirm proof.
- `tests/test_reviewed_source_observation_consumer.py` only for integrated producer-to-consumer proof.

The implementation handoff itself and the exact predecessor completion documents identified by PRIME belong in the activation lease. PRIME must name any applicable backward-looking sync set after re-anchoring. #1073 is already in the design base; no additional mutable predecessor handoff was found at that base. This draft allocates no unnamed documentation writes.

No Core code/pin, public request schema, candidate schema, UI application files, model/provider path, artifact-root redesign, corpus editing or new store is leased. The existing-object authoring proposal type currently supports object/link-existing/relationship/merge; link-existing translates to an alias. It does not already expose an observation proposal. Reuse its exact existing-object reference and source/parent guard meaning in the internal helper; do not claim its public UI route supports an attribute or silently reinterpret an alias action. If the existing typed package/trusted confirmation primitives cannot express the dependency or inspection requirement within these paths, stop and return the exact owning gap before extending the lease.

## 5. Prepare, review and confirm guards

Prepare seals both proposals and their evidence against the exact current parent and candidate/source identity. Attribute selection alone fails if its subject is neither selected as a new node in the same atomic contribution nor present on the pinned parent. Apply that check to single- and multi-slice reconstruction; the backend enforces it even if the UI dependency is bypassed. Never auto-add the node or attribute to the selection.

Confirm preserves the existing package digest, selected-assertion identity, source/catalog reproof, qualified identity binding and parent CAS. Source, candidate, evidence, description, subject, selection or parent drift invalidates the prepared package. An unselected companion must not enter the finalized review, read facet or Agent claims.

## 6. Evidence required for review

1. A create-new recap node produces a distinct source observation with the exact qualified subject, text/kind, source revision, campaign/session and evidence. Empty/unverified/held cases produce none; existing-identity support is not duplicated.
2. Review shows the text and provenance, defaults the companion off, and exposes a slice-qualified node dependency. Node-only selection remains valid and yields no description claim. Attribute-only selection for a missing subject fails; selected node plus attribute succeeds. Existing subject on the pinned parent permits observation-only selection through a fresh package.
3. Changed text, source digest/span, subject, selected assertions or parent fails the owning prepare/reconstruct/confirm guard. Repeated identical confirmation follows existing idempotency behavior.
4. Through a disposable Core database at the pinned version, finalized publication creates the object with canonical summary unchanged and exposes exactly the selected observation through native complete-object retrieval. Authored parent objects, relationships, identities and provenance remain intact.
5. Through ordinary Buddy selected-World object expansion and answer validation, the observation becomes a source-observation claim carrying review, contribution, publication revision, source revision and citation/span anchors. Its actual source opens and the reviewed quote is present. A no-model answer-validation witness is required in the PR; a real ordinary Agent answer is an explicitly activated execution witness after review, not a provider call during implementation tests.
6. A source-proven existing-subject follow-up makes no node-create, alias, merge or canonical-summary effect. Its new package/review uses the current parent, preserves all original authored fields and the old publication, and yields the selected observation in both actual Core retrieval and the ordinary Buddy/Harness facet. A wrong publication/assertion/source/candidate binding, missing or changed current subject, held identity, unselected observation, partial review or parent drift fails or yields no observation as appropriate.

Run the focused mapper, identity/selection, review projection, reviewed confirmation and source-observation consumer cohorts. Tests must exercise the producer-to-publication-to-consumer boundary; injecting a fabricated observation into only the consumer does not close this slice. Record exact head, command and result; never label a deselected owning integration witness PASS.

## 7. Existing C2S1 publication and full-corpus use

Do not edit or reseal the existing C2S1 package, finalized review or publication. The original 38-item package pins the old parent `rev:680c246047d67f9fe0293ee90526f670`; its node-create plan has expired. Re-preparing the original preview through the ordinary create path can encounter qualified-ID occupancy or surface ambiguity and is not the follow-up procedure.

The internal observations-only helper takes exact existing-object references proved from the C2S1 finalized publication at `rev:63513018ac05c26bc623fb3dfa324876`. For each of the four subjects, it verifies the publication/review/contribution digests, selected accepted node assertion, exact source artifact/revision, candidate node and description/evidence basis, and the source-local qualified subject carried by that assertion. The historical publication must be on the current parent's lineage, and the exact subject/kind must remain active and compatible on the current parent. No label join, positional preview-ID reuse, new identity resolution, merge decision or caller-only node-ID override supplies that proof.

The existing node description may supply candidate text for a NEW observation proposal only after its source/span support is rechecked. Its previous node acceptance never becomes automatic attribute acceptance. The helper emits only separately reviewed attributes, binds the historical proof plus current parent/source/candidate digests into a fresh sealed effect, and uses the existing finalized-review confirmation path. Confirm re-proves those references and parent CAS. It must not invoke NodeCreate, alter aliases or identities, replace canonical summaries, or reseal an old proposal.

After this capability merges and a separate execution packet is activated, independently review and select these new observations and confirm them as a new child revision. First prove the procedure on a disposable clone. Then the separately activated retained-World execution must show the descriptions in actual Core and Buddy/Harness reads, with the old canonical fields unchanged. A no-model source-rich answer/citation witness closes the consumer capability; model answer quality remains a subsequent separately measured product witness.

For later retained corpus sessions, each prepare uses the same producer behavior against its current parent. Review identity and description selections explicitly; process verified deltas with parent CAS and preserve authored content. This handoff authorizes no full-corpus batch execution and resolves no held identity question.

## 8. Activation and stops

PRIME checks current main and active PR/worktree leases, formally reviews this exact design PR head, records the accepted contract branch/commit, implementation base/Core pin and any applicable predecessor sync set, then explicitly activates one isolated serial implementation lane. The pushed reviewed branch is portable contract authority under PRIME's exception; landing on main is not an additional activation gate. This unreviewed design head itself authorizes no implementation or database writes.

Stop for a Core reader/materializer change, new term/schema/store, required identity-policy change, authored-summary overwrite, unreviewed/default-selected description, evidence weakening, hidden provider call, production database write or path beyond the activated lease. The reader eligibility extension is unnecessary while this producer can express the existing reviewed attribute shape; consider it only after demonstrating that the current producer contract cannot safely represent the explicitly reviewed statement.

