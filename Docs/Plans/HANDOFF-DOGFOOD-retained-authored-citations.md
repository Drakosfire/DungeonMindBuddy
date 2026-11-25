# DOGFOOD: cite retained saved-page evidence without reacquisition

ACTIVE serial successor to delivered4715/e57. Alan's writer/context cleanup goal
explicitly includes evidence-bound citations, long-chat reuse without another
search, fixing remaining gaps, reviewed merges, backups and Actions deployment.
DOGFOOD owns this bounded slice. Current main e699ab91711c2ddeaa2afb3df93fa077162f9d56
is policy/publisher authority; the retained runtime stack lives on the reviewed
serving lineage. Current base codex/dogfood-retained-citations-c034-base at healthy serving
c034ff63ac35675d3644b43f653e9290e88ff087 (image c16a2027), preserving the
reviewed guest Buddy/Play Buddy and trace release. The initial6a base was
superseded before merge; no prior branch was rewritten. Implementation branch
codex/dogfood-retained-authored-citations in existing dogfood-ci-one-app checkout.
Re-read actual serving before publishing; never change rollback pins alone.

Ordinary action and visible result: after Buddy has read a saved authored page,
ask it to quote/cite that evidence later in the same long conversation while a
different page is open. The reply must offer a clickable citation reopening the
exact captured historical saved revision, with no source reacquisition and no
page modification. Current failure695186de completed with correct quotes but
no citation: historical text is supplied, but no citable saved-page selector is
offered. Private reproduction/latency evidence is in external
buddy-check.pending-release.w1eihyha/live-app212-acceptance.json.

One coherent capability, not a new retrieval or authoring system. Version new
retained captures with presentation policy retained_conversation_semantic_v4;
keep old v3 producing frames and decoding unchanged. The V3 event kind stays
unchanged; only the new presentation policy enables retained citation references. Derive a distinct retained
saved-page reference from the existing admitted full related_authored row,
original source basis and producing occurrences. Do not fabricate RelatedPageRead,
selection/inclusion events, source settlements, fresh-read counters or authority.
Existing RelatedPageClaim/PageReference and authenticated citation-open transport
may select the derived reference. Models receive existing local page aliases,
meaningful source text/title and historical scope, never host IDs/hashes/receipts.

Eligibility: exact related_authored role, nonempty title, UUID document, valid
World/revision/visibility, full raw text SHA matching the saved basis, and joined
approved original occurrences. Exclude working drafts and partial saved sections.
Derive opaque completion-scoped selectors only from the validated admission and
context index; reject collisions/duplicates with acquired reads. Citation opening
requires the completed claim, equal page pin and current conversation/World access,
then returns frozen text. Never reread or substitute current page contents.
A reader fence APP0213 is required because old212 rejects the new presentation
policy; no data rewrite is authorized. Existing native Core reuse is unchanged.

Exclusive write set: this handoff; backward-looking settlement in
HANDOFF-DOGFOOD-app212-serving.md; src/application_state/agent_conversation/
{types.py,retained_conversation.py,build_source_free.py,build_related_pages.py,
native_writer.py,native_build_work_view.py}; apps/live_control_server/services/
build_related_pages.py; new migration20261125_0213_retained_authored_citations.py;
focused additions to tests/test_build_source_free_protocol.py and
tests/application_state/test_pending_build_storage.py (existing owned test paths). No frontend
change is expected because the public citation/opening shape already exists.
Inspect cumulative diff before expanding this boundary. No edits to ONBOARD's
service.py, agent_turn_service.py or existing retained tests: open4706 overlaps
those paths. Open4714's trace/UI lease is also excluded. Split/transfer explicitly
if any excluded path becomes necessary; Git conflicts are not coordination.

Verification: minimum focused SDK→completion→stored PostgreSQL readback→existing
citation-open endpoint tests, full long-chat/history and zero acquisition, plus
v3 no-offer/replay, invalid role/World/basis/body/title/occurrence/selectors,
alias collisions and current-access loss. Preserve existing claim/pointer/CAS and
rollback invariants. Audit actual serialized model requests for host metadata.
Use one exclusively owned App benchmark_run_e27fc178267a4d7cbc90bf173dd3ecfe,
OID210452, cluster7711451860937605159, evaluator788881785ebc:32769 and existing
exclusive executor lock/readonly owner receipt. Reuse serially, no new clone or
full contents scan; shared Core is read-only and need not be touched. Close all
workers/connections. No full backend/frontend/project suites.

Delivery: independent exact-head review, commit/push/open this one assigned PR,
then authorized merge; publish actual serving lineage through main Actions with
current guest options, exact immutable image and compatible213 recovery. Reuse
reviewed App-fence transport but qualify a NEW213 packet/images and fresh archive;
never reuse212 ACK. Deploy only through Actions; verify exact STAGED/LIVE/public
checks and the original live citation follow-up, citation click/readback and page
reuse/save/reopen. Record latency and actual limits. Full cleanup goal remains
active until its complete requirement audit passes.

Working-tree diagnostics before commit:41 focused protocol cases passed4.68s
(including actual SDK completion/stored binding/citation opening, legacy no-offer,
current access before/after read, collisions and source/owner tampering). One real
SQL constraint/readback/fence case passed3.17s on the same owned App; bounded16
historical production-format rows decoded under213 source. Workers/connections
closed. These are diagnostics, not exact-head qualification. A final missing-
occurrence refusal was added afterward; run the focused selectors again at the
committed SHA and retain external results before exact-head review.

User narrowed the active goal to PR4723 and its actual citation deployment/app
acceptance. General writer audits, onboarding and unrelated features are excluded.
The original ebf00e9b3df71c8ba24eaf9f21f0cec8bb134101 citation implementation
passed independent source review and exact42protocol/1SQL checks. Current-serving
adoption preserves its citation code unchanged; repeat only those focused owning
checks and exact-head review after this source/base update. Publication must use
the merged current-base PR and current guest flags, not obsolete6a rollback pins.
