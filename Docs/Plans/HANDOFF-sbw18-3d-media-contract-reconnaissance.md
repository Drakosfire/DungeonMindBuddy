# HANDOFF — SBW18 3D media contract and provider/storage reconnaissance

**Created:** 2026-07-22  
**Status:** DEFERRED / NOT READY FOR IMPLEMENTATION — dispatch only after `SBW17` dogfood and an operator selects a concrete 3D use case and provider candidate.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw18-3d-media-contract-reconnaissance.md`  
**Workstream:** `SBW18`  
**Repositories:** `Drakosfire/DungeonMindServer`, `Drakosfire/DungeonMindBuddy` design inputs; any implementation must be split into repository-owned successor PRs.

> This is a reconnaissance/design capability, not authorization to add model URLs to `AssetRefV1`. It must end with a concrete contract decision and separately dispatchable Server/Buddy implementation handoffs, or a documented no-go.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Select one product use case/provider/storage model | Yes | Design authority | No | Include |
| Define typed 3D media/job/preview/variant contract | Yes | Yes | No | Include as design outcome after selection |
| Prove one fixture-backed delivery path | No; required feasibility proof | No production write | Minimal | Include if provider selected |
| Implement Server generation/storage API | Yes | Yes | No | Successor Server PR |
| Implement Buddy selection/projection | Yes | Yes | Yes | Successor Buddy PR |
| Rigging/animation/print guarantees | Yes | Yes | Yes | Exclude unless selected use case requires it |

**Selected capability:** determine whether and how DungeonMind should represent and deliver one concrete class of generated 3D asset, producing an accepted contract and split implementation plan rather than overloading image fields.

**Why included rows share one invariant:** provider/use-case selection, contract design, and one proof artifact are necessary to establish whether a 3D media contract is implementable; production Server and Buddy behavior are distinct successors.

## §1 Mission

The design agent can select a concrete 3D use case and prove a typed media/job/storage contract so future implementation can support models honestly without widening image-only `AssetRefV1`.

**Invariant**

```text
A 3D asset is a distinct typed media resource with durable canonical files, preview imagery, generation provenance/job state, variants, ownership, and delivery requirements; it is never represented as an image URL with a model extension.
```

**Mission falsification test**

```text
This is not one reconnaissance slice if it starts implementing production generation/storage/UI before use case, provider, formats, licensing, retention, CDN delivery, and ownership semantics are accepted.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §13.2; results of `SBW16–17` image dogfood; current DungeonMind CDN/storage/security contracts |
| Repository rules | `AGENTS.md`; repository ownership boundaries; external-agent PR loop; no cross-repo implementation PR |
| Base revision | Record exact Server and Buddy main SHAs at dispatch |
| Predecessor contract | Image-only `AssetRefV1`, provider-owned CDN asset identity, Buddy media selection contract |
| Exact input consumed | Operator-selected primary use case, provider candidates, format/storage/delivery constraints, real sample outputs/terms |
| Named successor | Separate DungeonMindServer media generation/storage contract PR; separate DungeonBuddy consumer/selection/projection PR |
| What remains false | No production 3D generation, storage, selection, or rendering ships from this handoff |
| Explicit non-goals | generic file platform, arbitrary upload, universal 3D viewer, multiple providers, rigging/animation/print guarantees without selected need |

### Required operator selection before dispatch

Choose exactly one primary use case:

```text
A. tabletop miniature / printable model
B. VTT token model / turntable display
C. encounter/environment prop
D. rigged character for animation
```

The default recommendation for first investigation is **B: VTT token model / turntable display** because it requires fewer print/manifold/rigging guarantees than A or D while still proving canonical model + preview + variants + web delivery. This is a recommendation, not a silently accepted decision.

Also select one or at most two provider candidates for comparison. Do not perform an open-ended market survey inside implementation.

Read in order:

1. integration design §13.2
2. `SBW16–17` handbacks and actual image asset/storage/selection behavior
3. current DungeonMindServer asset models, CDN storage, deletion/retention/security policies
4. current supported content types/range requests/CDN headers
5. provider official API/schema, terms, licensing, retention, and sample output documentation
6. target consumer constraints in current web/desktop/VTT surface

## §3 Observable-path inventory

This is reconnaissance; inventory the intended future paths and whether the proposed contract can represent them.

| Future path | Required question/proof | Same invariant? | Owning future boundary |
|---|---|---:|---|
| Submit generation job | Can provider accept bounded source/prompt/assets and return stable job ID? | Yes | Server provider adapter |
| Poll/receive job state | Are queued/running/succeeded/partial/failed/cancelled states observable? | Yes | Server job store/API |
| Store canonical model | Which file is canonical, with what MIME/format/size/hash? | Yes | Server CDN/storage |
| Store preview | Can a durable image preview/turntable be generated and linked? | Yes | Server media pipeline |
| Store variants/LOD/source files | Which variants are necessary and how related? | Yes | media contract/storage |
| Deliver over CDN | Are MIME, CORS, range requests, compression, and cache headers correct? | Yes | CDN/runtime |
| Validate output | What minimum structural/size/security validation applies? | Yes | Server validation |
| Select/bind in Buddy | Can existing media selection generalize safely or require a distinct model selection contract? | Yes | Buddy consumer |
| Render/decline | Can client support selected format and fail honestly? | Yes | Buddy projection/viewer |
| Delete/retain | Who owns provider/CDN cleanup, retention, and derived variants? | Yes | Server asset lifecycle |
| License/use | What metadata must persist to respect provider/output terms? | Yes | contract/audit |

## §4 Files in scope — allowlist

This handoff itself is design/reconnaissance. A dispatched agent may change only documentation and checked-in sanitized fixtures.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Design/DESIGN-3d-media-contract-v1.md` | Accepted or proposed typed contract and decisions |
| Create | `Docs/Reports/REPORT-3d-media-provider-storage-reconnaissance.md` | Evidence, provider comparison, delivery proof, risks, no-go/decision |
| Create | `Docs/Plans/HANDOFF-<future-server-3d-media-slice>.md` | Separately reviewable Server successor if approved |
| Create | `Docs/Plans/HANDOFF-<future-buddy-3d-media-consumer>.md` | Separately reviewable Buddy successor if approved |
| Create | `tests/fixtures/media/3d/<sanitized-contract-fixture>.json` | Optional provider-neutral contract fixture only |
| Create | `tests/fixtures/media/3d/README.md` | Fixture provenance/limitations; no large binaries |
| Modify | roadmap/tracker only if operator accepts implementation successors | sequencing/status update |

### Bounded discovery exception

```text
Directory: DungeonMindServer asset/CDN docs and code; DungeonMindBuddy media consumer docs/code
Maximum additional changed paths: 0
Allowed path kinds: read-only inspection only
Decision rule: this reconnaissance may inspect implementation but must not patch production code
Required report: cite exact paths and current constraints in the design/report
```

Large model binaries, provider credentials, private sample assets, and unlicensed outputs must not be committed.

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| modifying image-only `AssetRefV1` to allow model MIME | dishonest compatibility break |
| production provider adapter/job API | separate Server PR |
| production model upload/CDN pipeline | separate Server PR |
| Buddy 3D selection/viewer | separate Buddy PR |
| arbitrary user uploads | generic file/security capability |
| supporting multiple use cases/providers in v1 | obscures requirements |
| rigging/animation | only if selected use case D |
| manifold/printability guarantees | only if selected use case A |
| automatic conversion among every model format | separate media processing capability |
| generated large binaries in Git | repository hygiene/security |

## §6 Investigation and contract requirements

### Required contract shape

The report/design must resolve at least:

```text
MediaAssetRefV1 or ModelAssetRefV1:
  schema/contract/version
  asset_id
  media_kind: model_3d
  provider/provider_asset_id?
  role: token_model | miniature | environment_prop | rigged_character | other selected enum
  canonical_file:
    url
    mime_type
    format
    byte_size
    sha256
    compression?
  preview_image: AssetRefV1
  variants[]:
    variant_id
    role: source | optimized | lod | printable | texture_pack | turntable?
    file ref / relationship
  dimensions/bounds/units?
  polygon/vertex count?
  texture/material metadata?
  validation_status/issues[]
  generation_provenance:
    job_id
    provider/model/version
    source asset IDs
    prompt/input digest, not necessarily raw hidden prompt
    created_at
  license/usage metadata?
  lifecycle:
    status
    retention/deletion owner
```

```text
ModelGenerationJobV1:
  job_id
  status: queued | running | succeeded | partial | failed | cancelled
  progress? bounded/provider-neutral
  requested use case/output profile
  input refs/digests
  output asset IDs[]
  warnings/errors[]
  provider operation ID?
  timestamps
  idempotency key
```

Do not finalize field names until provider and existing Server conventions are inspected. The design must state which fields are authoritative, optional, derived, and provider-specific extension points.

### Format decision

Choose one canonical delivery format for the selected use case. For web/VTT, likely candidates include glTF/GLB; for printable miniature, STL/3MF may be relevant. This document does not pre-decide the format. The report must justify:

- canonical versus source/variant format;
- MIME type and browser/client support;
- embedded versus external textures;
- compression/decoder requirements;
- file-size budgets;
- CDN range/CORS/cache needs;
- validation/security concerns.

### Provider comparison matrix

Compare selected providers on:

- API maturity and authentication;
- asynchronous job semantics/idempotency/webhooks/polling;
- input modes and provenance;
- output formats and quality consistency;
- texture/material support;
- generation latency and failure modes;
- pricing/rate limits;
- output ownership/licensing/commercial use;
- provider retention/deletion;
- model safety/content policy;
- durable download window;
- sample output size/validation.

Use official provider sources and real sanitized responses where possible. Clearly separate fact, provider claim, test observation, and inference.

### Delivery proof

If a provider is selected, produce the smallest safe proof without production code:

1. Obtain or use an authorized sample result.
2. Record provider response/job/output metadata in a sanitized fixture.
3. Verify canonical file MIME/format/hash/size.
4. Verify a local/static test server or current CDN configuration can serve required MIME and range requests, without deploying production changes.
5. Render or inspect using an existing off-the-shelf viewer/tool; do not build a product viewer.
6. Record unsupported/failure behavior.

If credentials/provider access are unavailable, the result may remain contract/design-only, but must not claim a live provider proof.

```text
Input:
  selected use case + provider evidence + current storage/CDN/client constraints

Output:
  accepted/no-go design, provider decision, typed contract, delivery proof or explicit missing evidence,
  and separate Server/Buddy implementation handoffs

Invariant:
  3D remains a distinct typed media/job contract

Failure behavior:
  no selected use case/provider -> stop, no speculative universal design
  licensing/ownership unresolved -> no-go/block implementation
  durable download/storage impossible -> no-go/block
  CDN cannot serve required MIME/range securely -> successor infrastructure decision before generation
  sample output invalid/too large -> adjust profile or no-go
  provider response cannot support stable job/asset identity -> reject provider for v1

Replay / idempotency:
  design records required generation idempotency semantics
  sample proof is reproducible from committed sanitized metadata where licensing permits

Trust boundary:
  Verifies: official contract evidence, sanitized response shape, file hashes/MIME/size, current CDN/client capabilities
  Records without proving: provider quality claims not tested, future performance at scale
  Rejects: arbitrary model URL as image, unlicensed samples, secrets, undocumented provider assumptions
```

### §6A State and fallback matrix

The design must complete a future-state matrix for job submission, polling, success, partial output, provider unavailable, malformed model, storage failure, CDN failure, unsupported client format, deletion/retention, and retry. No fallback may silently convert a model URL into an image asset or label a preview as the canonical model.

### §6B Identity matrix

The design must distinguish:

- provider job ID;
- provider output/model ID;
- DungeonMind stable asset ID;
- canonical file/variant IDs;
- preview image asset ID;
- Buddy selection target/role;
- URL as locator, never identity.

It must define rename/retry/duplicate/provider-regeneration/derived-variant behavior.

### §6C Persistence and replay matrix

The design must specify job and asset stores, atomic/partial points, idempotency, restart recovery, provider download expiration, variant creation, retention/deletion, compatibility, and whether any job can succeed with partial assets.

### §6D Predecessor-to-consumer mapping

Map current `AssetRefV1` and `ThreatMediaSelectionV1` concepts to what is reusable versus explicitly not reusable. Preview images may reuse `AssetRefV1`; canonical models may not.

## §7 Verification ownership map

| Guarantee | Boundary | Evidence required |
|---|---|---|
| Contract does not overload image fields | design schema review | distinct media/job types and mapping table |
| Provider evidence uses real vocabulary | report/fixture | official schema + sanitized response provenance |
| Licensing/retention/ownership resolved | report | cited official terms/docs or explicit blocker |
| Canonical format/delivery requirements proven | fixture/local delivery proof | MIME/hash/size/range/CORS/viewer observations |
| Identity/job/idempotency complete | design matrices | no URL identity or hidden latest |
| Server/Buddy work split | successor handoffs | one capability/repository each |
| No production code changed | diff | documentation/fixtures only |

Required commands/scenarios:

```bash
# validate any JSON fixtures with a small checked-in schema/test only if one is created
# inspect current CDN/static configuration without changing it
# record HTTP headers/range behavior for authorized local/sample file
# run an existing viewer/tool against the sample when available
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Not applicable until a provider and authorized sample are selected. When available, use an existing viewer and non-production delivery path; do not build a product viewer or generation UI.

## §8 Required handback

Include exact Server/Buddy base SHAs, selected use case/provider decision, source citations, fact/claim/inference labels, contract and all matrices, sample fixture provenance, delivery proof limitations, licensing/retention/storage decision, no-go items, separate successor handoffs, changed paths, and confirmation that production code remains unchanged.

## §9 Acceptance rubric

- [ ] One concrete use case and provider scope is selected, or the report explicitly stops with the missing operator decision.
- [ ] Image-only `AssetRefV1` remains unchanged.
- [ ] Distinct model asset and job contracts cover canonical file, preview, variants, provenance, lifecycle, ownership, and delivery.
- [ ] Identity never relies on URL.
- [ ] Licensing, retention, deletion, and commercial-use constraints are resolved or block implementation.
- [ ] Canonical format/MIME/CDN/client requirements are explicit and evidenced.
- [ ] Provider claims are distinguished from observed proof and inference.
- [ ] Server and Buddy implementation are separate future handoffs.
- [ ] No production generation/storage/viewer code ships.

## §10 Reviewer protocol

Review the selected user use case before schema details. Reject generic “support 3D” language. Audit official evidence, identity, job states, commit/partial points, durable download, licensing, deletion, MIME/range/CORS, size/validation, and repository ownership split.

## §11 Re-review protocol

Begin from prior findings and recheck the whole contract when provider/format/use case changes. A provider substitution invalidates job/identity/storage assumptions and requires full matrix review.

## Stop conditions

Stop if:

- the operator has not selected a use case;
- no provider candidate is selected;
- licensing/output ownership is unresolved;
- provider output cannot be downloaded durably into owned storage;
- stable job/output identity or idempotency is absent;
- required MIME/range/CORS cannot be served securely;
- the proof requires committing large/unlicensed binaries or credentials;
- one implementation PR would need to modify both repositories.

## Final dispatch check

- [ ] `SBW17` image selection dogfood is available.
- [ ] Operator selected one use case and provider scope.
- [ ] Documentation/fixture-only allowlist is accepted.
- [ ] Production implementation remains split and false.
