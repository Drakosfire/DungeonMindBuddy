# PROMPTS: fresh Build semantic initial context

Status: MERGED AND DELIVERED; ordinary fresh-turn proof remains open.
PR2196 merged at38c3e11ff03f2d299c0b5c56249e456aa025eb86. Reader UI
f8ffef8aa45ccbc13287975858f9e289386245ef preceded API
aff601828a012087f145e90baec47f9e04ea6e37 and fence127; retained data was
unchanged. PR2206 subsequently delivered API5149e2985231fcdf1845ab1993d21dca84d8c8e3,
retaining this behavior. The topology below records the original delivery plan;
it grants no active write lease.

PRIME owned design/implementation under the operator's highest
priority to remove host metadata from product prompts. Independent design critique
approved using the existing initial-input receipt codec rather than another
authorization event or ledger. The prior source head was independently reviewed;
this re-anchored delivery still requires exact-head review, CI and ordinary proof.

## Topology and ownership

Serial from current main 6f882ecdabcbdcd5fccea59fd5a1dc8f4c3ee4df in the existing
buddy-context-loop checkout/dependencies. PR2195 is already merged/delivered.
PR2205 is merged and delivered as API integration
bb56e91c857b26540d24d1f2f8d3a6b0aac08153; retain its request-proof/replay fix.
Prior reviewed source da46cb3e37baf7ac905688ac23dc54a277f08ccc remains pinned in
refs/codex/reviewed-heads/pr2196-da46cb3. Rebase this slice onto current main,
review/verify, merge and deliver UI reader before API fence127. Then rebase and
settle descendants in order2197,2199,2200; do not mutate those heads concurrently.
No new checkout/environment/provider call or primary database write is allocated.
Local verification uses generated disposable databases on54329. Runtime write
lease remains released until the protected delivery is re-anchored/reviewed.

Held Play2172 exact4b57a7cd66fad17df1106a16f0bc2be3c29ec8c3 remains held.
Its PR-body PRIME authority settlement2026-11-07 supersedes the old ACTIVE shared
file lease while held: prompt changes may use their own bounded handoffs, without
resuming Play or modifying Play behavior, UI, Runs or sessions. INGEST owners are
outside scope. Preserve the independently prepared2194 candidate and recipe.

## Outcome and owning contract

Fresh native Build requested-work selection sends semantic context only, without
DecisionIntent IDs/phase/duplicate questions, accounting, capability/draft hashes,
conversation/pointer/document identity or identity-only reference records. The
existing host interaction/capture remains unchanged. Preserve actual request,
page title, target kind/selected text, allowed outcome meaning, actual dialogue,
object-only proposed cards, selected/deferred steps, human reference labels and
source extents, and local related-page questions. No arbitrary text scrubbing.

Use a Build-only NativeProviderInput V2 in the existing receipt's assembler_version
union as the host-only wire-format discriminator. Keep NativeProviderInputV1 and
NativeReviewedActionInputV1 exact. Only fresh Build initial selection emits V2;
reviewed/auxiliary requests must not silently fall through as fresh V2. Add one
no-op forward reader fence127 over126. This is input presentation, never a new
source, provenance, publication or capability authority.

Keep the frozen counter and limits host-side. Before dispatch/APP acceptance,
reconstruct/compare the exact semantic state and full indexed question set from
actual host interaction, captured request/capability and locked catalog. Preserve
exact SDK bytes/hash, outcome, scope, revision, stale-target, menu/resolver,
capability, selected operation, arguments and destination checks. Bind host machine
request identity to semantic input and locked submission scope; actual broker
operation identity retains durable Turn/attempt. Do not merely delete the old
prompt-state capability comparison: its invariant must remain at the existing
frozen capability/action owner. Never use client labels as read/write authority.

For related-page votes, resolve question index against the existing locked catalog,
then use its host pointer. Preserve all real historical readers. The existing
strict UI receipt reader must accept V2 for Build only, in the same slice: shipping
an input codec that the ordinary surface cannot read is not a usable capability.
No visual redesign, legacy executor fallback, new global sanitizer or limit raise.

## Exclusive expected write set and review map

- This handoff.
- Docs/Plans/HANDOFF-RETRIEVAL-native-request-proof.md (truthful predecessor settlement).
- src/application_state/agent_conversation/native_context.py (initial codec/Build-only gate)
- src/application_state/agent_conversation/build_intentional_response.py (semantic projection/request binding)
- src/application_state/agent_conversation/build_related_pages.py (current indexed semantic offer proof)
- src/application_state/agent_conversation/build_decision_context.py (host select-phase admission)
- src/application_state/agent_conversation/service.py (locked receipt codec dispatch only)
- apps/live_control_server/services/build_jev_driver.py (current first state and host correlation)
- apps/live_control_server/services/build_related_pages.py (same versioned indexed question/vote owner)
- apps/live_control_server/services/build_jev_dispatch.py (host projection phase)
- apps/live_control_server/services/build_jev_harness.py (actual SDK context selector)
- apps/live_control_server/services/plan_source_turn.py (actual fresh Build V2 capture)
- src/application_state/migrations/versions/20261107_0127_build_initial_context.py
- apps/live-control-ui/src/api/types.ts (same closed receipt codec literal)
- apps/live-control-ui/src/shared/surfaceNativeProtocol.ts and its test
- tests/test_surface_native_context.py
- tests/test_surface_native_build_ordinary.py
- tests/test_build_decision_context.py
- tests/test_build_related_pages.py

If another current owning contract or file is necessary, checkpoint the coupling
and partition before expanding. These components form one indivisible current
input/acceptance/reader capability; helper-only or codec-only releases are unusable.

## Verification and remaining scope

Prove actual SDK/APP serialized wire sentinel absence and preserved semantic bytes;
object-only plan/questions/connected-page/relationship context; duplicate labels;
source/object extents; indexed related-page mapping; wrong title/user/allowed ops,
proposed work/capture/capability/menu/destination; replay and exact historical wire.
Bad bindings fail before paid transport. Run strict UI codec tests and native
initial/related-page/source/authoring owning tests. Review cumulative parent-to-head
diff, get independent Bugbot review, push/open the one PR, satisfy CI and protected
delivery, then ordinary dogfood. Preserve original failure/corpus/drafts/state.

All other prompt roles, reviewed auxiliary input, final evidence selection, writers,
References operator acceptance and measured generic retrieval remain open. Do not
claim overall prompt cleanliness, latency improvement or goal completion here.

## Re-anchor after CI and request-proof delivery

CI setup optimization #2203 is merged and measured twice without losing existing
cases. #2205 passed independent source/integration/delivery review, all seven
product checks and ADVERSARY's five retained-capture plus 25-negative-control
assessment. Actual owned API moved from b6182730 to bb56e91c with schema126,
UI unchanged and exact retained-table/session conservation. Old prepared API
integrations are explicitly invalidated and must be recomposed; do not reuse
an old API tree that omits the proof correction. The prepared UI source/release
may be reused only after exact blob and current reader/base verification.

The rebase applies the same bounded routing presentation change; it must not
resume held Play/citation work or widen to final writer/auxiliary prompting.

## Re-anchored local verification

The implementation range-diff is unchanged against prior reviewed098684418/
da46cb3; only parent history and consuming settlement change. On current main
6f882ecd, 100 focused context/accounting/actual initial SDK/source-owner and
oversized proof completion/replay cases pass in16.81s. Strict UI protocol52 cases
and TypeScript build checking pass. No new provider or live state changes.
The original broader legacy GM-authority fixture failure remains recorded in the
prior evidence; this focused rerun does not claim that unrelated full suite.
