# HANDOFF — SBW17 Durable image selection and Threat/statblock-form binding

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW10` and `SBW16` merge; re-anchor candidate asset refs, Threat Sheet composition, and durable state root.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw17-durable-image-selection-binding.md`  
**Workstream:** `SBW17`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability: select one already-generated durable image asset for one exact presentation role on a Threat or statblock binding/form, persist that choice, and compose it into existing projections. Do not generate, upload, edit, delete provider assets, change mechanics, or support 3D.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Persist selected provider asset for a typed role | Yes | Yes | Yes | Include |
| Support Threat-level and binding/form-level targets | No; two target variants of one media-selection contract | Yes | Yes | Include under same invariant |
| Display selection in Threat Sheet/shared renderer slots | No; required observable proof | No | Yes | Include |
| Generate images | Yes | Existing contract | Yes | Predecessor `SBW16` |
| Upload/crop/focal edit/delete asset | Yes | Yes | Yes | Exclude |
| Graph-store media binding | Yes | Yes | Yes | Exclude from v1 unless repository authority explicitly requires it; this handoff chooses a dedicated Buddy selection store |
| 3D media | Yes | Yes | Yes | `SBW18` deferred |

**Selected capability:** the GM can choose a durable image from known candidate assets and assign it to a typed presentation role that survives reload and appears on the composed Threat/statblock view.

**Why included rows share one invariant:** target variants and projection display are facets of one mutable selection record; generation and provider asset lifecycle remain separate.

## §1 Mission

A GM can bind a provider-owned image asset to a Threat or exact statblock form role so portrait/token/art display survives reload and projects consistently without changing mechanics identity.

**Invariant**

```text
A media selection references one exact provider asset_id and one exact target/role; selection changes only DungeonBuddy presentation state and never changes StatblockDefinitionV1, definition_digest, graph identity, or provider asset ownership.
```

**Mission falsification test**

```text
This is not one slice if implementation must also generate/upload/edit/delete assets, add graph media ontology, alter mechanics revisions, or support non-image/3D formats.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §13.1 and durable ownership table; `SBW16` typed assets; `SBW10` Threat Sheet |
| Repository rules | `AGENTS.md`; no arbitrary URL deletion/storage; server-owned provider credentials; external-agent PR loop |
| Base revision | Actual merged SHA containing `SBW10`, `SBW16`, and current state-store conventions |
| Predecessor contract | Durable typed `AssetRefV1` values attached to exact candidates; exact Threat/binding IDs; shared renderer media slots |
| Exact input consumed | Source candidate ID + exact asset ID, exact target kind/ID, exact role, expected selection version |
| Named successor | `SBW18` 3D media contract; later image editing/upload if dogfood proves need |
| What remains false | Asset binary/lifecycle remains provider-owned; no graph write or mechanics change |
| Explicit non-goals | image generation, upload, crop/focal editor, delete CDN asset, arbitrary URL, graph media nodes, 3D, player visibility policy redesign |

Read in order:

1. integration design §13.1
2. merged `SBW16` candidate asset fixtures/safe display
3. merged `SBW10` Threat Sheet and `SBW08` binding identities
4. current DungeonBuddy file-backed/versioned store precedents
5. current shared renderer media slots/tokens
6. Server `AssetRefV1`/`AssetBindingV1` generated types only for vocabulary; Buddy owns selection

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Open candidate assets | Preview only | Select eligible exact asset | Yes | workbench/media UI |
| Select Threat portrait | No durable selection | Store target `threat:<id>`, role `portrait` | Yes | selection service/store |
| Select Threat token | No durable selection | Store target, role `token` | Yes | service/store |
| Select binding/form image | No durable selection | Store exact binding ID and role `full_body|alternate|encounter_art` per allowed matrix | Yes | service/store |
| Replace selected asset | Undefined | Optimistic versioned replacement for same target/role | Yes | store/service |
| Unbind selection | Undefined | Delete/tombstone selection record only; provider asset remains | Yes | store/service |
| Reload Threat Sheet | No selection composition | Selected refs load and render | Yes | projection service/UI |
| Candidate expires | Could lose source context | Selection retains exact durable AssetRef snapshot/identity and source provenance | Yes | store |
| Asset/CDN unavailable | Preview breaks | Selection remains; unavailable image state | Yes | renderer/UI |
| Mechanics revision/binding upgrade | Could accidentally clear media | Target semantics explicit: Threat-level persists; binding-level stays on exact binding and does not rebind silently | Yes | store/projection |
| Arbitrary asset URL request | Potential attack | Reject; resolve asset by trusted candidate/cache/reference identity | Yes | service/security |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_media_selection.py` | strict target/role/asset/version models |
| Create | `apps/live_control_server/services/threat_media_selection_store.py` | atomic versioned selection repository |
| Create | `apps/live_control_server/services/threat_media_selection.py` | trusted candidate asset resolution, select/unbind/list |
| Create | `apps/live_control_server/routes/threat_media.py` | browser-safe selection API |
| Modify | `apps/live_control_server/main.py` | mount router |
| Create | `tests/test_threat_media_selection_store.py` | round-trip/version/replace/unbind proof |
| Create | `tests/test_threat_media_routes.py` | trusted asset/target/security proof |
| Modify | `apps/live_control_server/services/threat_sheet_projection.py` | compose selected media refs |
| Modify | Threat Sheet projection tests | target precedence/unavailable proof |
| Modify | `apps/live-control-ui/src/api/types.ts`, `liveApi.ts`, `liveApi.test.ts` | selection API |
| Create/Modify | `apps/live-control-ui/src/statblocks/media/MediaSelectionPanel.tsx` and tests | choose/replace/unbind known assets |
| Modify | `StatblockWorkbenchModule.tsx` and tests | launch selection from candidate assets |
| Modify | `ThreatSheet.tsx`, shared renderer media slots, and tests | display selected media |

### Bounded discovery exception

```text
Directory: apps/live_control_server/services/, apps/live-control-ui/src/statblocks/media/, merged candidate cache and Threat Sheet areas
Maximum additional paths: 7
Allowed path kinds: trusted AssetRef resolver, state-root helper, media slot style, binding-upgrade interaction test, focused tests
Decision rule: include only to resolve a known asset, persist one selection, or compose it into existing views
Required report: identify target/role precedence and exact state root; no graph or provider lifecycle path
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| generating/regenerating images | `SBW16` |
| arbitrary upload or URL | new trust/storage boundary |
| crop/focal point/editor | independently useful UI/data contract |
| deleting provider/CDN asset | provider ownership/lifecycle separate |
| graph external asset node/edge | v1 selection store chosen to keep scope bounded; revisit only through architecture PR |
| mechanics revision/digest changes | media is presentation state |
| automatic transfer from old binding to upgraded binding | explicit target semantics; no silent rebind |
| player visibility/admissibility redesign | use existing Threat/surface policy |
| 3D/model formats | `SBW18` |

## §6 Implementation contract

### `ThreatMediaSelectionV1`

```text
schema: dmb_threat_media_selection_v1
selection_id
version
campaign_id
world_id?
target:
  kind: threat | statblock_binding
  id: exact threat node ID | exact binding ID
role: portrait | token | full_body | encounter_art | alternate
asset:
  provider
  asset_id
  mime_type
  canonical_url
  source_candidate_id?
  provider_role?
  variant_key?
  width?/height?
  created_at?
source:
  selected_from_candidate_id?
  selected_from_asset_brief_id?
selected_by
created_at
updated_at
```

Store an exact bounded `AssetRefV1`-derived snapshot sufficient to render/recover after candidate expiry. The snapshot is not provider asset authority; `provider + asset_id` is identity.

### Target/role rules

- `target.kind=threat`: permit `portrait`, `token`, `encounter_art`, `alternate`.
- `target.kind=statblock_binding`: permit `full_body`, `token`, `encounter_art`, `alternate`; confirm final matrix against product design before dispatch.
- One active selection per `(campaign, target kind, target ID, role)` in v1.
- Replacing uses optimistic `expected_version`; stale replacement fails.
- Unbind removes/tombstones only the selection record. It never calls provider deletion.
- Validate exact Threat/binding existence and campaign scope through graph projection/read at selection time. Persist exact IDs; later graph removal yields unresolved target state, not rebind by label.
- Resolve asset from a trusted candidate asset list/cache or a trusted already-selected record. Request never supplies canonical URL/MIME as authority.

### Composition precedence

- Threat-level portrait/token represent campaign identity and persist across binding revision upgrades.
- Binding-level form art applies only when rendering that exact binding.
- For a renderer slot, an exact binding-level role may override a Threat-level fallback only according to a fixed documented matrix. Never first-win by list order.
- Missing/unavailable image does not fall back to an unrelated candidate asset. A named Threat-level fallback is permitted only if the role matrix says so.

```text
Input:
  exact trusted candidate_id + asset_id
  exact target kind/ID + role
  expected selection version for replace/unbind

Output:
  versioned ThreatMediaSelectionV1 and composed selected media views

Invariant:
  exact provider asset and target/role; mechanics/graph/provider ownership unchanged

Failure behavior:
  candidate/asset missing or expired before first selection -> reject unless durable AssetRef can be resolved from trusted cache/record
  arbitrary URL/MIME mismatch -> reject
  target missing/denied/wrong campaign -> reject
  role incompatible -> reject
  stale expected version -> 409, no change
  atomic write failure -> prior selection remains
  CDN unavailable -> selection remains, display unavailable
  binding upgraded/superseded -> binding-targeted selection remains attached to old exact binding and may become non-active/unresolved; no silent transfer

Replay / idempotency:
  same exact target/role/asset with current version -> idempotent no-op or version-stable response
  replacement with different asset requires expected current version and increments exactly once
  duplicate network delivery under same expected version cannot increment twice
  unbind repeated -> idempotent absent/tombstone result under declared policy

Trust boundary:
  Verifies: trusted asset membership, provider/asset ID/MIME/URL snapshot, target exact identity/campaign, role matrix, expected version
  Records without proving: artistic quality, licensing beyond provider metadata, visual fit
  Rejects: arbitrary URL, raw bytes, provider deletion, mechanics mutation, label target identity
```

### §6A State and fallback matrix

| Path | Loading | Success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry |
|---|---|---|---|---|---|---|---|
| Asset selection source | read exact candidate/assets | eligible assets | none | candidate unavailable/expired blocks new selection unless trusted durable cache | malformed ref rejects | candidate status irrelevant after trusted ref | regenerate images/new candidate |
| Target validation | graph exact read | target accepted | 404/denied | graph unavailable blocks write | campaign/ID mismatch | superseded binding policy explicit | retry |
| Select/replace | load current record | active selection/version | no prior = create | state store unavailable | atomic fail closed | expected version conflict | reread/retry |
| Unbind | load current | removed/tombstone | already absent idempotent | store unavailable | fail closed | stale version conflict | reread |
| Threat Sheet render | load selections | role-precedence result | no media state | store/CDN unavailable honest | malformed selection ignored with diagnostic/fail safe | old binding media not transferred | retry image/load |

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Asset | exact provider + asset ID | metadata mismatch integrity failure | No URL identity | stored snapshot/ref |
| Threat target | exact graph node ID | none | No label/alias final | selection scope |
| Binding target | exact binding ID | superseded remains exact | No role lookup | no silent transfer |
| Role | exact enum and target matrix | invalid rejects | No | uniqueness key |
| Selection | deterministic or opaque selection ID + version | duplicate target/role one active | exact-key lookup | optimistic update |
| Candidate | exact source provenance only | expired after selection okay | No name | not target identity |
| URL | locator only | may become unavailable | No identity | snapshot presentation |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Create selection | strict versioned JSON record/index under Buddy state root | target/role/asset snapshot exact | same exact selection idempotent | schema version strict | unbind |
| Replace | atomic version increment | all identity fields exact | stale rejected | no implicit migration | replace back using version |
| Unbind | delete/tombstone per policy | absence/status exact | repeated safe | provider asset untouched | reselect asset |
| Compose/read | derived list/view | exact active selections | safe repeat | unknown schema fails/diagnostic | N/A |

### §6D Predecessor-to-consumer mapping

**Grounding source:** real `AssetRefV1` fixtures from `SBW16`, graph Threat/binding views, Threat Sheet projection.

| Predecessor field | Selection field/behavior | Rule | Proof |
|---|---|---|---|
| asset provider/ID/MIME/canonical URL/variant/role | stored asset snapshot | resolved server-side from trusted candidate | security/route test |
| candidate ID/asset list | selection source/provenance | exact membership | source test |
| Threat node ID/campaign | target | exact graph read | target test |
| binding ID/statblock/revision context | target/form scope | exact binding | upgrade test |
| role | uniqueness/display slot | fixed matrix | role tests |
| selection version | replace/unbind concurrency | exact expected value | stale tests |
| Threat Sheet | selected media slots | deterministic precedence | projection/UI tests |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Arbitrary URL cannot select | service/route | negative request tests | rejected/zero write |
| Exact asset membership/target validated | service | candidate/graph fixtures | accepted/rejected matrix |
| Versioned replace/unbind safe | store/route | stale/replay tests | one increment/prior preserved |
| Candidate expiry after selection does not erase asset ref | store/projection | reload fixture | selected snapshot remains |
| Mechanics digest unchanged | workflow/non-mutation | before/after assertions | exact equality |
| Binding upgrade does not transfer media silently | integration | old/new binding fixture | old selection remains exact; new has none |
| Role precedence deterministic | projection/UI | matrix tests | exact chosen slot |
| CDN unavailable honest | UI | image error test | selection/locator retained |

Required commands:

```bash
uv run pytest tests/test_threat_media_selection_store.py tests/test_threat_media_routes.py tests/test_threat_sheet_projection.py -q
cd apps/live-control-ui && npm test -- --run <MediaSelectionPanel/ThreatSheet/workbench tests> src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Generate candidate images, select a portrait and token for a published Threat, reload the Threat Sheet, replace one selection, unbind another, and simulate CDN failure. Upgrade the mechanics binding and prove Threat-level media persists while binding-level art does not silently transfer. Confirm definition digest is unchanged.

## §8 Required handback

Include target/role/precedence matrix, state root/schema, trusted asset resolution proof, base/head, paths, commands/results/provenance, live selection/reload/replace/unbind/CDN/upgrade evidence, baseline failures/waivers, and confirmation that no generation/upload/delete/graph/3D/mechanics change ships.

## §9 Acceptance rubric

- [ ] Selection uses exact trusted provider asset ID, never caller URL authority.
- [ ] Target and role are exact, typed, campaign-valid, and versioned.
- [ ] Replace/unbind use optimistic concurrency and replay safely.
- [ ] Durable selected ref survives candidate expiry and reload.
- [ ] Threat Sheet/media slots use deterministic precedence.
- [ ] Mechanics digest and graph identity remain unchanged.
- [ ] Binding upgrade never silently transfers binding-level media.
- [ ] Provider asset is never deleted by unbind.
- [ ] No upload/edit/graph-media/3D capability ships.

## §10 Reviewer protocol

Begin at the trust boundary: caller sends IDs, backend resolves trusted AssetRef. Audit state identity/version, target/role matrix, candidate expiry, binding upgrade, CDN error, and mechanics non-mutation. Search for caller URL/MIME persistence, delete calls, label target lookup, graph writes, and model MIME.

## §11 Re-review protocol

Rerun arbitrary URL, asset membership, target/campaign, role matrix, create/replace/stale/replay/unbind, candidate expiry, precedence, CDN failure, binding upgrade, and mechanics non-mutation tests after every fix.

## Stop conditions

Stop if:

- candidate asset refs are not durable enough to persist after candidate expiry;
- no server-side trusted asset lookup/cache exists and request would need to trust caller URL;
- target/role ownership requires graph media ontology rather than a bounded Buddy store;
- state root/version semantics require a broader storage architecture decision;
- binding upgrade cannot distinguish exact old/new binding targets;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor real AssetRef and Threat/binding view shapes.
- [ ] Freeze target/role/precedence matrices.
- [ ] Choose delete vs tombstone selection policy explicitly.
- [ ] Confirm `SBW18` and upload/edit/provider lifecycle remain false.
