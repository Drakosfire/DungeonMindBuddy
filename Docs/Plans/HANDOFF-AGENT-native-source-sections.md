# AGENT — exact native source sections

## Authority

PRIME design slice; base620579bba10138dd7b73e2340a7fb4ca59776a85,
branch codex/native-source-section-design, existing buddy-context-loop checkout.
Serial: one design PR, Architecture critique and independent Bugbot review before
PRIME merge. Exclusive design writes: this handoff, predecessor settlement in
HANDOFF-AGENT-session-excerpt-attribution.md, and ROADMAP-demo.md. No runtime,
provider, database or serving change. Open PR census2026-10-22: no overlapping lane.
Design #1631 mergedcfa0dee7299eac72042ea432a78e29d5e8cbb802 after two Bugbot
cycles and Architecture approval. Body-read/ledger/routing implementation remains
BLOCKED until bounded ACTIVE leases name concrete paths and activation/migration
gates. The metadata-only prerequisite is leased separately in
HANDOFF-AGENT-source-origin-verifier.md; it grants no content read or citation.
Buddy owns producer, APP ledger, immutable body storage and UI. Core owns native
source identity/provenance and Graph scope. If existing Core contracts cannot
prove this join, return a bounded Core contract request; do not bypass the owner.

## Outcome and gap

Buddy can follow an admitted encounter source into its statblock appendix and
cite the exact saved section by useful source name and location. Generic across
adventures; source possibilities remain distinct from played facts.
Conks has the appendix in its saved source, but current Plan reads expose only
Graph-pinned encounter passages. The Tree subject is a Location. Build whole-source
admission and discovery do not authorize Plan arbitrary reads. Existing Build
section events bind a workspace basis, not native source identity; related-recap
navigation is recap-specific. Neither can be relabeled unchanged as this proof.

## Admission

Start only from an actual validated Graph operation in the current turn's frozen
World/visibility/Graph scope. Join its admitted anchor provenance to native source
artifact, exact source revision and full-source SHA-256. Verify revision belongs
to artifact, artifact belongs to World, domain, active lifecycle and visibility.
A historical revision need not equal mutable current revision; historical pinning
never bypasses fresh access checks. SourceAdmissionReceipt alone does not prove
current Graph scope or publication. Capture the actual donor event and provenance.
Missing/ambiguous/inaccessible joins yield explicit gaps. Display labels, caller
paths, conversation mentions, controller routes and Build discovery are not donors.

## Concrete producer and storage join

The proposed verifier composes existing APIs without loading body content:
`services.retrieval.resolve_source_anchor(projection, anchor_id=...)` establishes
an exact Core `SourceAnchorResolution`. Require found/can_open_source and equality
of its snapshot with the frozen scope and donor ledger event. Compare anchor ID,
evidence ref, artifact/revision and locator identity with the donor's validated
pin. Fetch `services.bundle.sources.get_revision(native_revision_id)`; require
exact ID, artifact and valid full digest. Revalidate artifact ownership, domain,
active lifecycle and current visibility from the resolution. Persist the complete
normalized resolution/provenance digest, donor event ID/result hash and exact
source tuple, not a bare revision string. APP verifies the donor and proof joins;
the trusted producer owns Core API verification. It must reject a changed native
result rather than overwrite donor identity. Do not use the presentation helper
`_source_revision_digest` as sufficient authorization: it omits this full join.

Body authority already exists in `application_state.source.service`:
`persist_source_markdown` transactionally inserts immutable `source.revision` rows
and rejects conflicting artifact/digest/revision assertions. Graph-run registry
`_persist_source_authority` captures registered recap/worldbuilding bytes before
its ExtractionRun becomes canonical. `get_source_markdown` reads by exact artifact
and digest, optionally local revision UUID. Native source revision IDs and APP
source revision UUIDs are DIFFERENT namespaces: persist both, joined by exact
artifact/full digest plus verified World/domain/lineage and body hash. Do not cast
one ID into the other. The receipt binds the returned APP UUID as well as native
revision; historical reopening supplies all three APP lookup selectors and checks
the original native tuple. The store has no source access grant: the producer must
perform fresh Core and managed-World access checks first. No new copying or body
capture occurs during a query. Sources without this retained body return a gap.

A later Build edit leaves old digest-keyed rows intact. If explicit deletion or
retention removes bytes, return unavailable. A retained row never restores access:
for acquisition and historical open require current authenticated managed-World
binding, exact pinned Core resolution, active artifact and admissibility under
current metadata. Deactivation, source visibility denial, World reassignment,
missing artifact or broken lineage denies reopening even when bytes remain. The
implementation must verify these behaviors against actual Core re-projection;
if resolution does not enforce them, this is a Core gate before activation.
The source-origin prerequisite now exercises real Core re-projection: current
retraction, unknown visibility, foreign World and missing artifacts deny a pinned
source, while an allowed old source revision and old Graph revision remain exact
after mutable source/current Graph heads advance. Managed-World authentication and
authorize-before-body-load remain later owner gates; this metadata proof alone
never grants content access.

## Exact sequence

Use distinct native-source-section events and citations. Never fabricate a Graph
anchor/evidence ID to fit SourceReadAnchorReceiptV2. Implementation assigns exact
schema versions; these joins are mandatory:

1. Persist navigation authorization before loading a body: turn/attempt, frozen
   scope, donor Graph event/provenance, native artifact/revision/full digest,
   verified source name and operation. Validate donor against ledger and producer
   native provenance result.
2. Read immutable APP bytes by artifact/full digest, verifying body hash and native
   identity/World/domain/encoding/access. No mutable latest or filesystem fallback.
3. Derive deterministic heading/section catalog from those exact bytes. Bind its
   hash and handles to source tuple, selector algorithm version and inclusive
   one-based line ranges. Labels are untrusted navigation data, not evidence.
4. Plan Jev selects an offered handle in its existing decision phase; native Play
   Hermes selects through its registered tool lifecycle. The shared parent authorizes
   its exact range and allowance before slicing/returning excerpt bytes. Reject
   arbitrary model paths/ranges and handles from another catalog.
5. Persist successful read linked to authorization, source tuple, selector/range,
   raw text, UTF-8 excerpt hash and returned characters. Full-source and excerpt
   digests are different. Reuse exact_saved_section lossless line semantics.
   Truncation/partial reads cannot acquire an enough receipt.
6. Bind successful reads to the actual writer attempt/envelope and included event
   IDs. APP complete_turn reconstructs all joins, segment text/hash and inclusion.
   Trace/controller assertions alone do not confer citation authority.
7. Persist source-section citation variant with named source and section/page/line
   locator. Page labels require source metadata, never line-number inference.
   Attribute authored source material; no Graph truth or played outcome upgrade.
8. Authenticated World/turn/citation-index opener reconstructs stored completion,
   rechecks access and rereads exact immutable bytes. Verify original source/range/
   excerpt hash or report unavailable; later Build edits never replace old bytes.

Keep Graph citations and session authored excerpts distinct. Preserve historical
readers/records, but add no legacy execution fallback. Do not mutate frozen carrier
policy text. Version new producer/APP/strict UI capability and pair activation so
an old consumer cannot inadvertently accept new authority.

## Reuse and measurement

Verify source bytes/catalog once per authorized scope; recheck access as required.
Deduplicate exact source/range/digest acquisitions. Historical reuse requires a
durable validated donor/inclusion chain. Do not reread whole source per section
or send whole bodies to Jev. Expose overlap and charge newly included content
where accounting supports it; otherwise select nonoverlapping ranges and report
honestly. Catalog/body IO is real work: measure physical bytes/time separately
from logical selected excerpt characters, reuse and actual model usage.
Use existing budgets explicitly; no new arbitrary caps, silent truncation or
writer repair calls. Budget exhaustion yields a gap/selection opportunity. Reuse
Plan Jev decisions and one Plan writer, with no model call just to find headings.
Play remains native Hermes: use its existing tool-call/producing-attempt lifecycle,
not a new Play Jev controller or a change to the frozen NativePlay carrier.

The distinct typed citation must retain managed/native World and turn, producing
attempt/envelope, included read IDs, native and APP source revision IDs, full and
excerpt digests, catalog/selector, inclusive range, verified source name/locator
and successful status. Completion remains source-only (or a mixed answer with
separately typed Graph/session support); no section can satisfy a Graph citation.
APP verifies segment text/hash and support against the actual included envelope.

Persist separate navigation/body-read, section authorization/read, reuse and
provider-inclusion accounting events. One body acquisition records physical bytes
once; scope-local sibling slices record zero fresh body IO. Exact section reuse
is a reuse event, never another physical read. Logical writer inclusion counts
the union of included exact source ranges, with overlap reported explicitly;
repeated frames still report actual provider input tokens. APP validates these
counters against the event chain, including failed and budget-denied operations.
Concrete event schemas/migration and policy integration are activation gates.

## Implementation and verification gates

A: producer+APP admission/catalog/read/receipt, reuse/accounting, exact provider and
completion joins, versioned source-only citation and historical opener contract.
B: Plan Jev routing and native Play Hermes tool routing, authenticated opener and
shared rendered named
citation consumer. Name concrete paths and migration in each ACTIVE lease. If
split into serial PRs, declare exact dependency and keep capability inactive until
paired: no Plan dispatch or Play tool registration until strict completion
reader, API/UI named citation renderer, authenticated opener and history/replay
consumers are deployed together. Preserve old completions unchanged. This design
presumes no Core runtime changes; the explicit Core verification gate above must
be resolved before granting a Buddy implementation lease.

Test actual producer→APP completion→reload→authenticated opener. Cover exact donor,
foreign World, denied visibility/lifecycle, wrong artifact/revision/full hash,
stale/ambiguous metadata, unauthorized body read, missing/forged/reordered events,
handle/range substitution, Unicode/newlines, full-vs-excerpt hash confusion,
writer omission/wrong attempt, fabricated Graph citation, duplicate/reuse charging,
original reopen after source edit, missing original bytes and unchanged historical
completions. Verify strict UI citation acceptance, useful names/locators and stale
response handling. Helpers alone do not prove the boundary.

Then retrieve the Conks appendix through ordinary controls with a real provider
and inspect its citation. Prepare mechanics in the shared editor, explicitly adopt
a successor and repeat scene→encounter→Play. Exercise Sheep and original swamp/Edge
for generality, quality, latency and call counts. No adventure-specific runtime,
console/SQL/manual-ID repairs or private corpus published on GitHub. These are
future acceptance gates, not claims established by this design.

## Predecessor

Session attribution #1630 merged620579bba10138dd7b73e2340a7fb4ca59776a85 after
one Bugbot cycle; matched API/UI on5202. A fresh5.6-second Conks answer separately
attributed three session excerpts; links reopened the exact saved review checkpoint.
Prompt guidance improved the reproduction, not deterministic semantic entailment.
Connected Conks encounter journey passed once, not full J1–J6. Second adventure,
original swamp/image, performance/resource proof and operator acceptance remain.
