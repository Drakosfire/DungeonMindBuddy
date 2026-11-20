# Native source inspection API adoption

Status: ACTIVE. Owner: PRIME. Topology: serial, based on Buddy
 e151ee4cae05a8eaca4a777d6df5843cd34abba5. Cross-owner authority:
DungeonOverMind PR101, merged 5aa1dc34e6a7e6e2dbb173d1ee7d053d3efa77b6,
Docs/Plans/HANDOFF-REFERENCE-native-source-catalog.md. Core slice A is merged as
0f86f1fd74af13fe8ff0597349c1cd3b37210a26, exact reviewed tree56fbe2a;
independent approval and all Core CI passed. This activates the API portion of B.

## One outcome and expected write lease
Authenticated GM clients can discover native source metadata and open one exact
source version without an active object Graph. Adopt Core's merged metadata owner,
existing source-context resolver, exact body reader and read-only repository.

Expected writes:
- this handoff
- pyproject.toml and uv.lock (Core pin only; no other dependency upgrade)
- apps/live_control_server/models/native_source_inspection.py
- apps/live_control_server/services/native_source_inspection.py
- apps/live_control_server/routes/native_source_inspection.py
- apps/live_control_server/main.py (router registration only)
- tests/test_native_source_inspection.py
- .github/workflows/hosted-validation.yml (owning test selection only)

Existing native Graph inspection can only open assertion-support sources and requires
an active Graph binding. Existing conversation body readers require retained turn
acquisition records. Neither is a human source-only metadata/opening endpoint; this
is the concrete transport gap. Reuse the existing strict selector/pin model where
its semantics fit; source-owner resolution must never call the object binding gate.
No new source identity, provenance store, index, body cache or publication authority.
Other lanes PR2079,2081,2082 own ingestion and its UI, disjoint from this write set.

## Adoption, boundaries and verification
Core owns admission, annotations, visibility, source membership and body/span/hash
verification. Remove no current conversation acquisition or Graph browser caller;
those remain separately exercised until their surface integrations adopt this API.
Do not fake provider grants for human inspection. Selection remains separate from
acquisition for a generated answer. This API adds no durable authored input schema.

Metadata requests must not read bodies. A selected read revalidates the exact World,
native identity, binding, knowledge revision, source pair and evidence ID through
Core. No foreign source or caller-provided labels grant access. Return unavailable
and partial coverage honestly, with no silent fallback or arbitrary result ceiling.
Campaign/session filtering and producer navigation labels are subsequent UI work;
this API declares World-wide GM source inspection, not narrower evidence restriction.

Verify ordinary authenticated HTTP source-only reads without entities/assertions or
active object binding; unauthenticated/player/foreign/malformed selectors fail closed;
late binding changes, old revision membership, missing metadata, reader refusal and
integrity failures stay explicit. Preserve native exact body proof fields. Exercise
existing source navigation and Graph inspection against the new Core pin and retain
original failures. Independently review the exact cumulative diff, then commit/push/PR
and merge under standing authority and owning checks.

## Resources and remaining goal
Reuse checkout/dependencies. Tests may use the merged Core source via PYTHONPATH;
do not sync the shared .venv while the owned API is using it. No runtime, provider,
retained-data or DB-mutation lease is activated here. Dependency delivery requires
its own reviewed API stop/install/restart and retained-state conservation. UI browsing,
recap/passage attachment, Plan/Play integration, restrictions and operator acceptance
remain open. No chronology implementation or compatibility executor is included.


## Serial source-browser adoption
Core155 is merged0f86f1f and Buddy2083 is merged/delivered4247484. Core156 is
mergedc2ea8d0624b75fb5c051d3368334d6f7fe7512a2, reviewed tree ddf8d13;
all owning CI and actual WorldKeeper consumer pass. The original consumer failure
is retained: native views also serve the general evidence reader. Both readers
now use one native metadata loader; the general reader is required, not obsolete.

ACTIVE source-browser successor: PRIME, branch `codex/native-source-browser`, base
b20e0b0d72a756d6315605e1501059317628aa9a (includes independently merged2084/2085),
serial after Core156. Authoritative bounded
write/resource contract is the private `native-source-browser-handoff.json` in
PRIME's established runtime-evidence directory. Outcome: ordinary human source
browsing and exact opening through the shared Build/Plan/Play World browser.
Adopt the existing source-only APIs, Core origin, APP source metadata/name helper,
page inventory, native auth/recovery, exact inspection pins and Markdown renderer.
Move the existing pin comparator into its shared inspection contract module;
retain citation disclosure for its separate live callers. No second catalogue,
receipt lookup loader, store, provenance policy, endpoint or schema migration.

Source labels and type/campaign/session filters are navigation, never evidence
restrictions or read authority. Resolve recap labels by exact producer revision,
digest and World; use page names as current presentation with explicit metadata
revision difference. Missing labels must not hide otherwise admitted sources or
claim complete filtered coverage. Body requests occur only on explicit selection
and retain the exact native pair/pin; stale/substituted results fail without fallback.

Expected writes extend the earlier API lease with the existing API service/tests,
Core pin/lockfile only, UI source inspection API/types/auth tests, native source
browser/tests, shared World browser/tests/CSS, shared pin comparator and its Graph
consumer, and the existing hosted UI test selection only. Shared pins and hosted
test selection are serialized after merged2085; preserve its GenerationEngine pin. Verify owning HTTP, actual Core source-only reads, UI filters and absence
of arbitrary result caps, exact pins, late World responses, retry and unchanged
Graph/picker/auth callers; typecheck/build, independent cumulative review and CI.
No shared dependency install, runtime restart, retained DB write or provider call
is activated here; delivery needs protected resource and conservation checks.
Source/passage attachment, acquisition/restrictions, remaining surface integration
and operator acceptance stay open; this browser alone does not establish completion.


## Source browser settlement and passage successor

Buddy2086 merged eb2f0afe805f473b22bfb2bccf4709a5ad90e210 after independent
approval and all seven applicable checks. Protected API/Core and UI delivery
preserved retained state. Ordinary source browsing/opening is verified in Build,
Plan and Play. The original stale-page asset failure during the successor runtime
deployment is retained; prior194 assets now remain byte-identical and the failing
chunk serves JavaScript. No attachment, restriction or surface acceptance is implied.
The source-browser write lease is closed. The serial exact-passage successor is
`HANDOFF-REFERENCE-native-source-passages.md`, based on the merged2086 revision.
