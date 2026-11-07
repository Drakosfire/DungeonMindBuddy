# RETRIEVAL: reversible source candidate scope

Status: ACTIVE for implementation after independent design approval by
/root/bugbot_classic_cli on2026-11-07. Runtime activation remains gated by
implementation/integration review and CI. PRIME owns the exclusive writes below.
PRIME owns this operator-authorized retrieval experiment. Base is remote main
9be15b1434f6d0adfbe1d3e3fbad903d4614c82c; branch
codex/native-source-candidate-scope in the existing context-loop checkout.
Topology: serial after delivered PR2181. Play2172 stays held; open INGEST lanes
own no proposed navigation/driver paths. No new checkout, environment or service.

## One outcome and boundary

Offer a smaller, reversible source candidate view when the actual query supplies
recognizable source/campaign/session hints. Expose an explicit native expansion
choice that restores every omitted still-admitted/unattempted source and section.
Narrowing and expansion stay together: filtering alone loses reachable context;
an unused expansion helper alone delivers no capability. Keep Graph discovery
semantics and all native source admission/read/grounding owners unchanged.

The frozen ordinary baseline has819 relevance votes over five native decisions,
37 reads and222897 UTF-8 bytes; the existing controller later called19 of those
units irrelevant (not independent gold). Source scope shadow819→349 is only a
hypothesis. Existing per-catalog specificity155→155 is not worth shipping alone.
Do not claim speed/coverage from a shadow, sorting, labels or helper tests.

## Explicit native expansion contract

Do not repurpose discover_more: that operation retains its Graph-search meaning.
Add a distinct native-corpus-expand navigation candidate in NativeBodyNavigation.
The handle binds the actual turn/attempt/query/context through existing hashes.
Its selection is recorded by the existing NativeRetrievalSelectedV1 owner under
select_candidates; no new read grant, evidence event or provenance authority.
Route this exact selected handle explicitly at the driver/navigator boundary.
Validate against the acknowledged current parent and exact handle, including the
actual selected result; do not silently accept an unknown handle. Selecting it
performs no Graph operation, source body read or fact acceptance. Other genuinely
selected narrow reads in the same batch retain their existing authorization.

Reconstruct expansion from matching acknowledged selections in the current
execution, not local persistent state or a blacklist. Expansion persists across
successive controller provider attempts in the same frozen retrieval execution;
it is not keyed to the current controller_attempt_id. Clear it for another
product turn/attempt, query, action, policy or context receipt. Recovery reopens
the broad view without reacquiring text.
Include a no-op reader-fence schema revision before delivery: an older API must
not ignore the new selected navigation action or reinterpret it after rollback.
No document/candidate/source/Graph rows are rewritten; downgrade is refused.

## Scope hints, not authority

Use source_display_metadata from the existing producer owner after Core admits
membership. Candidate/source identity and access remain the original Core pins.
Names, campaign IDs and session IDs supply lexical navigation hints, never fact
scope, chronology, source admissibility or publication authority. Recognize exact
source names, explicit campaign IDs and ordinary recap shorthand (C2S20, campaign
1, session16). Matching a campaign code inside a producer metadata ID is a weak
lexical hint, not a canonical campaign-number mapping. Keep every ambiguous
match and unknown/unclassified or stale-metadata source reachable in the first
view. If there is no positive recognized match, offer the original broad view.
Never derive identity from directories, filenames or manually curated story facts.

Filter both full-source and section offers by the same source-pair view. Keep
native search and actual authored references available under their existing
policies. Expansion returns the original broad catalog minus actual attempted
reads; it must not override any existing exclusive-reference restriction. Leave
lexical capture, matched-term receipt formats, Jev prepared-decision wording,
model allocation, writer selection, source reads and grounding unchanged.

Expansion takes effect immediately upon the acknowledged selection. By apply(),
the expanded offered view no longer contains the expansion action; dispatch must
recognize it explicitly against the original acknowledged parent and the exact
current selection. Reconstruct that state after reload without new IO/events.
Never add an unselected broad candidate to a mixed selected batch.

A generic entity/page name alone must not exclude recap sources. Exact source
names are retained in addition to explicit campaign/session hints. An unknown
campaign/session token, stale metadata or unavailable metadata stays in view.
Measure total and native-source ballots separately; saved-page choices remain.

## Exclusive expected writes

- This handoff; HANDOFF-ACTIVITY-completion-disclosure.md for predecessor settlement.
- apps/live_control_server/services/native_source_candidate_scope.py (pure hints).
- apps/live_control_server/services/corpus_source_navigation.py (candidate view).
- apps/live_control_server/services/plan_jev_driver.py (explicit native dispatch).
- tests/test_native_source_candidate_scope.py (pure/navigation contrasts).
- tests/application_state/test_surface_native_acquisition.py (actual SDK/APP/Core).
- tests/application_state/test_surface_native_decisions.py: extend the existing SDK
  fixture with native parent/auth/selection codecs for current-path tests only.
  This adopts the current producer rather than duplicating its large fixture;
  existing historical fixture cases stay unchanged.
- src/application_state/migrations/versions/20261107_0122_native_candidate_expansion.py
  (reader fence only, no row rewrites).

Any additional durable/public contract, owner or path requires a steward checkpoint.
Do not change frozen prepared-decision codecs or add a fallback execution pipeline.

## Verification and resources

Use existing dependencies and disposable APP fixture service54329 for owning tests;
no primary APP54331/Core54330 writes, no benchmark55447 access. Put test evidence in
the established private runtime-evidence root, not a new /tmp task directory.
No production resource mutation until independent review, CI and exact integration.

Prove the candidate reduction on frozen inputs, then actual admitted SDK selection
→ APP reload/recovery → native expansion → exact Core read. Expansion exposes all
omitted eligible candidates, never itself reads or establishes support. Cover no
matching scope, ambiguous sessions/campaign codes, unknown and stale metadata,
source/World/revision/hash drift, direct named source and unrelated/generic query,
mixed Graph/native discovery, forged/wrong-attempt expansion, both expansion and
narrow reads in one acknowledged batch, and preserved restrictions. Test the old
reader fence without rewriting retained documents. Inspect the cumulative diff.

Use paired decision-only diagnostics before ordinary original/contrast runs.
Retain exact hashes, votes, reads, bytes, rounds, elapsed time and citations. Keep
the writer fixed; no new ingestion, model comparison, publication or Graph curation.
Review/CI/merge/deliver in this one bounded PR. All expected checks must finish
successfully before merge; GitHub auto-merge is not a substitute for that audit.
The whole goal, References closure and operator acceptance remain open.

## Captured implementation evidence (not activation or goal completion)

Private retained evidence root is the established q01-published-graph-authority
runtime-evidence directory. native-source-scope-frozen-audit.json reconstructs
native candidate handles from exact captured acquisition prefixes and validates
all five baseline SDK envelopes against the preserved provider payloads. Total
ballots819→552, native offers586→314, with five explicit expansion choices. This
is presentation evidence, not a runtime latency/coverage result. Four paired
Jev1.14 decision-only calls retain their exact payloads/results in
native-source-scope-decision-{0,1}-{baseline,candidate}.json. The candidate
selects expansion on the post-search ballot; later ballots may broaden again.
No writer/model change, gold creation, World writes or ingestion occurred.

Owning checks: native-source-scope-checks.log39 passed, four inherited cases
deselected; three additional negative-hint cases20 pure tests total;
native-source-scope-sections.log7 SDK/APP/Core/fence cases passed;
native-source-scope-decisions.log32 passed. Four existing acquisition failures
reproduce with exact remote-main runtime and fixture code in
native-source-scope-inherited-tests.log. Two expect the older assertion subtype;
two assume a source extent stays selectable after a full-source read. Preserve those results;
no unrelated assertion/fixture repair belongs to this slice. Implementation
review, CI, delivery and actual ordinary/contrast latency remain pending.

Independent review of3a0c696 held metadata-loss recovery and mixed Graph/native
proof. The owning fix compares expansion against the exact acknowledged parent
request/hash/catalog, never against a refreshed display join. Tests now remove
display metadata after selection and restore it in later rounds, reject wrong
parent/attempt handles, and select expansion plus a real native Graph object in
one Core-backed shared execution before opening an out-of-hint native source.
Classic discover_more remains separately exercised by its existing driver suite.
Negative scope phrases without/exclude retain the broad view. The superseded
integration40c998 was never activated; its unused staging export was removed
after consumer/reference/tracked-file checks. The running API remains3c69b41d.

Review-fix owning evidence: native-source-scope-final.log8 shared native
SDK/APP/Core/fence cases passed, including the real mixed Graph/source case.
native-source-scope-classic.log32 unchanged classic-driver tests passed.
The22 pure hint contrasts and earlier SDK-fixture regression checks also pass.
The provider-free audit revalidated all five exact SDK envelopes with unchanged
ballot reduction; previously retained paid comparison envelopes are byte-identical
and were reused, not rerun. Independent revised-head review and CI remain gates.
