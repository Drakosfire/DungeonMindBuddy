# HANDOFF — SBW16 Optional candidate image generation

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW04` and current DungeonMindServer image-generation contract are re-anchored; may run in parallel with mechanics persistence/projection work.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw16-optional-image-generation.md`  
**Workstream:** `SBW16`  
**Repository:** `Drakosfire/DungeonMindBuddy` unless the dispatch gate identifies a required separate DungeonMindServer contract PR.

> Dispatch one capability: the GM may request optional image generation when creating/revising a candidate and inspect typed durable asset outcomes. Do not select/bind assets, change mechanics identity, add uploads, or implement 3D.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Allow `generate_images=true` on candidate generation/revision | Yes | Existing Server contract | Yes | Include |
| Display asset brief, durable image refs, and partial warnings | No; required result proof | No | Yes | Include |
| Select portrait/token/form role | Yes | Yes | Yes | Successor `SBW17` |
| Retry image-only generation after mechanics candidate exists | Yes | Possibly new Server API | Yes | Exclude unless current Server contract already supports it exactly; stop condition |
| Local upload/storage/delete | Yes | Yes | Yes | Exclude |
| 3D generation | Yes | Yes | Yes | `SBW18` deferred |

**Selected capability:** optional image generation is an explicit candidate-generation/revision request whose asset success/failure is visible and non-blocking.

## §1 Mission

A GM can request images while generating or revising a statblock candidate so DungeonMindServer may return durable CDN image assets and warnings without making image success a condition of valid mechanics.

**Invariant**

```text
Image generation is optional presentation work attached to a candidate outcome; mechanics definition/digest and candidate validity remain independent, and only typed provider-owned AssetRefV1 values are treated as durable assets.
```

**Mission falsification test**

```text
This is not one slice if implementation must also persist a selected asset role, modify graph/media state, upload local files, delete provider assets, regenerate images independently without an existing Server contract, or support 3D.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §13.1; DungeonMindServer `AssetRefV1`/candidate generation contract; tracker `SBW16` after decomposition |
| Repository rules | `AGENTS.md`; server-owned credentials/assets; external-agent PR loop |
| Base revision | Actual merged SHA containing `SBW03–04` and current candidate revise path when used |
| Predecessor contract | Candidate generation/revision requests; candidate payload asset brief/assets/warnings; readiness capabilities |
| Exact input consumed | Explicit user image-generation option plus existing candidate generation/revision input |
| Named successor | `SBW17` durable image selection/binding |
| What remains false | No asset is selected for Threat/statblock role; no media store or graph state changes |
| Explicit non-goals | uploads, provider settings UI, deletion, image editor/crop, media binding, 3D, mechanics save coupling |

Read in order:

1. integration design §13.1
2. current Server OpenAPI/types/fixtures for `GenerateCandidateRequestV1`, revise request, `AssetBriefV1`, `AssetRefV1`, asset warnings, readiness capabilities
3. merged `SBW03` request mapper and `SBW06` revise mapper if applicable
4. merged `SBW04` workbench/renderer media placeholder areas
5. `SBW01` readiness/error taxonomy

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Generate candidate default | Images deliberately disabled | Remains disabled unless explicit option enabled | Yes | UI/request mapper |
| Generate candidate with images | No product option | Send exact supported request flag/options | Yes | UI/service/client |
| Revise candidate with images | No product option | Supported only if real Server revise contract accepts it | Yes | UI/service |
| Server image capability unavailable | Readiness may expose | Option disabled or request yields typed non-fatal warning; mechanics may still succeed | Yes | readiness/UI/service |
| Full success | Assets may exist in payload | Show asset brief and durable typed refs/previews | Yes | workbench |
| Mechanics success/image partial failure | Not surfaced | Candidate remains usable; warnings visible | Yes | service/UI |
| Provider failure causing whole request failure | Possible Server behavior | Preserve typed failure; do not fabricate mechanics/image partial success | Yes | service/UI |
| Candidate reload | Assets in cache/payload | Same refs/warnings reload | Yes | candidate cache/read |
| Asset URL safety | Could render arbitrary | Render only typed supported image MIME/HTTPS CDN refs under existing safe-image policy | Yes | UI |
| Selection/binding | None | Still none | Yes | non-mutation proof |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/services/statblock_candidate_generation.py` | Map explicit image option to real Server contract |
| Modify | `apps/live_control_server/services/statblock_candidate_revision.py` | Only if real revise contract supports image request |
| Modify | candidate workflow request/view models | strict image option and result projection, no local asset schema fork |
| Modify | candidate routes/tests | request and partial warning proof |
| Modify | merged DungeonMind client only if operation types already exist but method mapping is absent | exact contract call |
| Add/Modify | captured candidate asset success/partial/unconfigured fixtures | real contract proof |
| Modify | `apps/live-control-ui/src/api/types.ts`, `liveApi.ts`, `liveApi.test.ts` | option/result mapping |
| Modify | `StatblockWorkbenchModule.tsx` | explicit option and asset outcome display |
| Modify | workbench tests | default/explicit/partial/unavailable/reload proof |
| Create/Modify | bounded statblock asset-preview component/style/test under `src/statblocks/media/` | safe image display only |

### Bounded discovery exception

```text
Directory: merged SBW01 integration package; apps/live-control-ui/src/statblocks/media/; generated contract fixtures
Maximum additional paths: 5
Allowed path kinds: readiness capability mapping, safe image component, generated type export, real asset fixture, focused test
Decision rule: required to request or display typed image outcomes; no selection store or provider-specific settings
Required report: identify exact Server behavior for partial image failure and supported MIME/URL fields
```

### Cross-repository gate

Before implementation, confirm DungeonMindServer supports the desired request through an existing published v1 route.

- If candidate generation/revision already accepts `generate_images` and returns durable `AssetRefV1`, remain DungeonMindBuddy-only.
- If the desired user path requires image-only regeneration after a candidate exists and no route supports it, stop and create a separate DungeonMindServer contract/implementation handoff. Do not hide a new Server API inside this Buddy PR.
- Do not modify DungeonMindServer and DungeonBuddy in one PR.

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| selecting portrait/token/full-body/encounter role | `SBW17` |
| durable Buddy media selection store | `SBW17` |
| graph/media binding | later selection capability |
| local upload or arbitrary URL | new trust/storage boundary |
| delete provider/CDN asset | ownership-sensitive separate capability |
| crop/focal/edit image | separate product capability |
| image-only retry endpoint if absent | separate Server PR |
| 3D/model MIME | `AssetRefV1` is image-only; `SBW18` |
| making mechanics acceptance wait for images | prohibited |

## §6 Implementation contract

### Request

- Default remains `generate_images=false`.
- Explicit UI option maps to the exact current generated request field; no provider name/model/prompt fields are invented unless contract already exposes them.
- If asset brief editing is supported by the Server contract, keep it bounded and typed; otherwise display the generated brief only.
- Readiness must truthfully indicate image generation availability when the downstream service exposes it.

### Result

- Candidate mechanics/validation state is evaluated independently from assets.
- Display `asset_brief`, `assets[]`, and asset-specific warnings using generated types.
- A durable asset requires provider-owned `asset_id`, supported image MIME/role/variant metadata, and canonical durable URL per Server contract.
- Transient provider URLs/data URIs/raw bytes are not persisted or labeled durable.
- No selection state exists in this slice.

```text
Input:
  existing candidate generate/revise request + explicit image option

Output:
  typed candidate with mechanics plus zero or more durable image refs and warnings

Invariant:
  image outcome cannot alter mechanics identity/validity or imply selection

Failure behavior:
  image capability unavailable before request -> option disabled/honest diagnostic
  typed mechanics success + asset warning/zero assets -> candidate success, media partial/failed state
  whole downstream request failure -> candidate failure under existing semantics; no fabricated partial
  malformed/unsafe asset ref -> omit from trusted render and show integrity warning; retain raw typed failure only within bounded diagnostics
  image load failure in browser -> broken/unavailable preview; ref retained

Replay / idempotency:
  candidate generation/revision follows existing request idempotency and creates/returns candidate identity
  reloading candidate shows same asset refs/warnings
  enabling images changes request semantics and must not reuse an idempotency key created for `generate_images=false`

Trust boundary:
  Verifies: readiness capability, exact request flag, typed asset ID/MIME/URL/role fields, safe render policy
  Records without proving: artistic quality, likeness, licensing beyond provider metadata contract
  Rejects: arbitrary user URL, data URI as durable asset, model/3D MIME, implicit selection
```

### §6A State and fallback matrix

| Path | Loading | Success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/expired | Retry |
|---|---|---|---|---|---|---|---|
| Option/readiness | load capability | selectable | capability absent → disabled | honest unavailable | mismatch diagnostic | refresh readiness | safe |
| Generate/revise | existing candidate loading | mechanics + assets | mechanics + zero assets/warnings | typed according to Server outcome | malformed ref warning/fail trusted asset | candidate expiry normal | new request/idempotency |
| Asset display | image skeleton | typed preview/ref | zero assets state | CDN unavailable/broken preview | unsafe MIME/URL not rendered | ref remains candidate metadata | browser retry |
| Candidate reload | exact candidate read/cache | same refs/warnings | no assets | candidate unavailable | schema fail closed | expired state retains ref metadata per existing policy | regenerate candidate |

No fallback to local image generation, arbitrary provider URL, old transient asset, or selected-media state.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Candidate | exact candidate ID | none | No | assets attached to candidate outcome |
| Generation request | exact request/idempotency including image flag | changed flag distinct | No | replay safety |
| Asset | exact provider `asset_id` | duplicate ID with different metadata integrity warning | No URL identity | durable ref |
| URL | presentation locator only | changes may be variants | No identity | never selection key |
| Role/variant | provider metadata/display | not selected use | No | candidate asset metadata |
| Mechanics digest | independent | must not change due solely to asset outcome if same mechanics | No | acceptance gate unaffected |

### §6C Persistence and replay matrix

| Operation | Representation | Round-trip | Duplicate/replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Candidate cache/read | existing typed candidate payload with asset refs/warnings | exact asset IDs/metadata | existing candidate semantics | generated contract version | cache disposable/non-authoritative |
| Request operation | existing idempotency record | image flag included | same request same result; changed flag conflict/new key | Server contract | N/A |
| UI preview | derived | ref retained across reload | deterministic | unsupported MIME honest | N/A |

### §6D Predecessor-to-consumer mapping

**Grounding source:** real Server asset-bearing candidate success, partial warning, and unavailable capability fixtures.

| Server field/outcome | Buddy behavior | Rule | Proof |
|---|---|---|---|
| `generate_images` request field | explicit option | default false | request tests |
| readiness image capability | option availability | honest mapping | readiness tests |
| asset brief | review disclosure | exact typed display | fixture |
| asset ID/provider/MIME/URL/role/variant | preview card | validate/render safely | asset tests |
| asset warnings | candidate media state | distinct from mechanics validation | partial fixture |
| whole error envelope | existing candidate failure | no fabricated partial | error tests |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Default images false | request mapper | focused test | exact payload |
| Explicit images true changes idempotency/request | service | tests | correct key/payload |
| Capability absent honest | readiness/UI | tests | disabled/diagnostic |
| Mechanics success + image failure remains candidate success | service/UI | partial fixture | mechanics review usable, warnings visible |
| Unsafe asset not rendered | media component | MIME/URL negative tests | no image request/render |
| Candidate reload retains refs | cache/route/UI | reload test | same asset IDs |
| Mechanics digest/acceptance unaffected by asset-only outcome | workflow tests | compare candidate/acceptance state | unchanged gate |
| No selection/media store | diff/non-mutation | path inspection | absent |

Required commands:

```bash
uv run pytest <candidate generation/revision asset tests> -q
cd apps/live-control-ui && npm test -- --run <workbench/media preview tests> src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Generate one candidate with images disabled, then one with images explicitly enabled. Show durable asset refs or typed image warnings, reload the candidate, and demonstrate mechanics review/validation remains usable when image generation is unconfigured or partially fails. Do not select an asset.

## §8 Required handback

Include exact Server route/fixture behavior, request/partial-state mapping, base/head, paths, commands/results/provenance, live asset IDs/warnings without raw secrets/URLs when sensitive, cross-repo stop result, baseline failures/waivers, and confirmation that no selection/upload/delete/3D ships.

## §9 Acceptance rubric

- [ ] Image generation is explicit and defaults off.
- [ ] Request uses the real Server contract and capability readiness.
- [ ] Mechanics and image outcomes remain independent.
- [ ] Partial image failure does not invalidate successful mechanics.
- [ ] Only typed durable image refs are trusted/rendered.
- [ ] Reload retains exact asset IDs/warnings.
- [ ] No asset selection/binding, upload, delete, provider settings, or 3D behavior ships.
- [ ] No hidden DungeonMindServer API is invented in the Buddy PR.

## §10 Reviewer protocol

Begin with real Server fixtures and partial-outcome semantics. Audit idempotency inclusion of the image flag, readiness honesty, safe image rendering, and mechanics independence. Search for selection state, arbitrary URLs, data URIs, provider credentials/options, raw bytes, and model MIME.

## §11 Re-review protocol

Rerun default/explicit request, capability absent, partial warning, whole failure, unsafe asset, reload, and mechanics-independence tests after every fix.

## Stop conditions

Stop if:

- the current Server contract cannot request/return images on candidate generation/revision;
- user-required image-only regeneration needs a new Server route;
- returned URLs are transient or lack durable asset identity;
- asset MIME/ownership/delete semantics are insufficient for safe display;
- image generation failure cannot be distinguished from mechanics failure truthfully;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor exact Server asset contract and readiness.
- [ ] Decide whether only generate, or generate+revise, supports images.
- [ ] Capture real partial/unavailable fixtures.
- [ ] Confirm `SBW17–18` remain false.
