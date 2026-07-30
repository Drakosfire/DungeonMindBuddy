# PATTERN — OpenAI Structured Outputs for complex statblock-class contracts

**Status:** ACTIVE pattern (codifies shipped behavior; additions proposed, not dispatched)
**Created:** 2026-07-29
**Base:** PR `#449` branch `agent/r0a-generation-validation-failure` (`6ceee3b4`)
**Trigger evidence:** [`../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md`](../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md) — `R0-A` `FAIL_PRODUCT` on opaque `definition_invalid`
**Sequencing authority:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md) (`DMS-VAL-01` → `BUDDY-VAL-01` → R0-A re-run)
**Constraint source:** OpenAI Structured Outputs guide, fetched live 2026-07-29 (`developers.openai.com/api/docs/guides/structured-outputs`)
**Code authority:** `DungeonMindServer` `statblocks_v1/` at current `main` (PR24 era)

---

## §1 Why this document exists

`StatblockDefinitionV1` is the most complex provider-facing schema we operate: 72 `$defs`, 57 object types, 210 object properties, an 8-branch mechanic union, and a 12-branch effect union used at 7 sites. It will not be the last contract of this class (graph extraction, ingest sidecars, planner envelopes, revise packets all trend the same direction).

On 2026-07-29 the real provider rejected a Mireward Latchling generation with a single generic message. We could not tell which of four materially different failure zones produced it. The immediate repair is `DMS-VAL-01` (typed diagnostics). This document is the durable companion: **how OpenAI Structured Outputs constrains complex contracts, what our compiler already does about it, and the design moves to reach for when the schema fights back** — so the next contract does not re-derive this from scratch.

Prior art lives on Server branches `feat/statblocks-v1-pr13-contract-models` (schema compiler + artifacts) and `feat/statblocks-v1-pr16-generation` (structured-outputs provider), hardened by `1c062b1` (context-aware metadata strip, anyOf, RechargeRange) and `9b4d628` (fail-closed unsupported constructs). This document codifies that shipped work as *the* pattern.

---

## §2 OpenAI constraint matrix (verified 2026-07-29)

| Constraint | Current rule | Consequence for us |
|---|---|---|
| Supported types | String, Number, Boolean, Integer, Object, Array, Enum, `anyOf` | Everything else needs a rewrite or fails |
| `oneOf` | **Not supported** | Rewrite to `anyOf` (lossless in practice only if branches are structurally exclusive — §6.2) |
| Composition keywords | `allOf`, `not`, `if`/`then`/`else`, `dependentRequired`, `dependentSchemas` unsupported | Conditional shapes are inexpressible → push to domain validation (§6.3) |
| Required | **All** properties required; optionality only via union with `null` | The all-required / null-union tax (§6.1) |
| Object closure | `additionalProperties: false` mandatory everywhere | Compiler enforces; also good hygiene |
| Root | Must be an object, never `anyOf` | Envelope your union inside a property |
| Value constraints | `pattern`, `format` (limited set), `multipleOf`, `minimum`/`maximum` (+exclusive), `minItems`/`maxItems` listed as supported | **Supported ≠ trustworthy authority** — see §5 zone 2; fine-tuned models lose all of these |
| Fine-tuned models | Additionally lose `minLength`/`maxLength`, `pattern`, `format`, numeric bounds, `patternProperties`, `minItems`/`maxItems` | If we ever fine-tune statblock generation, zone-2 constraints leave provider enforcement entirely |
| Size budget | ≤ 5000 object properties total, ≤ 10 nesting levels | We are at 210 / ~4 — comfortable, but monitor (§6.6) |
| String budget | ≤ 120,000 chars across property names, def names, enum values, const values | Watch enum-heavy growth (conditions, damage types) |
| Enum budget | ≤ 1000 enum values total; ≤ 15,000 chars for a single enum with >250 values | Spell/condition reference lists must not become schema enums |
| Key ordering | Output is produced in schema key order | Order identity fields first (§6.5) |
| Recursion | Supported (`#` root or explicit `$ref`) | Available if phase trees ever recurse |
| Unsupported schema | `strict: true` + unsupported construct → **request-time API error** | Fail-closed compilation beats a 400 at generation time |

Non-goals confirmed by the same source: JSON mode guarantees only parseable JSON, not schema adherence; function calling shares this constraint subset; prompt-only "return strict JSON" is rejected by `.cursor/rules/responses-api-structured-extraction.mdc` for extraction and by the same logic for generation authority.

---

## §3 `StatblockDefinitionV1` measured against the matrix

Artifacts: `statblocks_v1/domain/schema_artifacts/statblock_definition_v1.{canonical,openai-strict}.schema.json` (canonical 62,864 B, strict 48,857 B; the ~14 KB delta is mostly stripped `description` text — §6.4).

| Metric | Canonical | OpenAI-strict | Budget | Headroom |
|---|---:|---:|---:|---:|
| `$defs` | 72 | 72 | — | — |
| Object schemas | 57 | 57 | — | — |
| Total object properties | 210 | 210 | 5000 | ~4% used |
| Nesting depth | ~4 | ~4 | 10 | fine |
| `oneOf` sites | 8 | 0 (rewritten) | n/a | compiled away |
| `anyOf` sites | 55 (all null-unions) | 63 | n/a | — |
| Optional (nullable) sites | 55 | 55 forced-null | n/a | the tax (§6.1) |
| Objects with partial `required` | 51 | 0 | 0 allowed | compiled away |
| `pattern` | 14 | 14 | zone 2 | — |
| `minimum` / `maximum` | 30 / 12 | 30 / 12 | zone 2 | — |
| `minLength` | 18 | 18 | zone 2 | — |
| `minItems` | 9 | 9 | zone 2 | — |
| `enum` / `const` | 17 / 20 | 17 / 20 | 1000 enums | fine |

Union sites (canonical `oneOf`):

- `RuleElement.mechanic` — 8 branches (`AttackMechanic`, `SaveEffectMechanic`, `MultiattackMechanic`, `SpellcastingMechanic`, `PassiveMechanic`, `CompositeMechanic`, `PhaseTransitionMechanic`, `HumanAdjudicatedMechanic`)
- Effect union — 12 branches (`DamageEffect` … `HumanAdjudicatedEffect`) at 7 sites (`hit_effects`, `miss_effects`, `failure_effects`, `success_effects`, `CompositeMechanic.effects`, `PassiveMechanic.effects`, `PhaseTransitionMechanic.effects`)

---

## §4 The established compiler pattern (this is the pattern — reuse it)

`statblocks_v1/domain/schema.py` + `statblocks_v1/application/schema_compiler.py`:

1. **Two artifacts, one source of truth.** Canonical = `StatblockDefinitionV1.model_json_schema()` (the Pydantic model is the contract). Strict = deterministic compile of canonical. Both checked in, diffable, reviewable.
2. **Staleness is a build failure.** `compile_openai_definition_schema()` raises if the checked-in strict artifact ≠ fresh compile; `test_schema_artifacts_match_model_output` does the same in CI. The provider can never silently serve a drifted schema.
3. **Lossless rewrites only, explicit list.** `oneOf` → `anyOf`; single-branch `allOf` unwrap (multi-branch fails). Everything else in the unsupported keyword set (`prefixItems`, `patternProperties`, `unevaluatedProperties`, `unevaluatedItems`, `if`/`then`/`else`, `not`, `dependentSchemas`, `dependentRequired`) **fails compilation** — no silent drops (`9b4d628`).
4. **Metadata strip is context-aware.** `$schema`, `default`, `description`, `examples`, `title`, `discriminator` are stripped at *schema-node* level only; property names that collide (`ArmorClassProfile.default`, `StatblockFlavorText.description`) are preserved. Regression-tested.
5. **Closure assertion.** Every object gets `additionalProperties: false` and `required = properties`; `_assert_closed_objects` re-verifies the compiled artifact before it can be served.
6. **Property-path parity.** `test_canonical_and_provider_property_paths_match` proves the provider-facing schema addresses the same fields as the canonical contract.

Any new provider-facing contract (Buddy extraction passes, future Server generation surfaces) gets this same six-part treatment. Do not hand-write a "simplified" schema next to the model.

---

## §5 The four failure zones (diagnostic model for `DMS-VAL-01`)

The 2026-07-29 `definition_invalid` could have come from four zones with different owners and different fixes. `DMS-VAL-01`'s `phase` field must distinguish at least zones 2+3 from 4.

| Zone | Where enforced | Example | Surfaces today as | Fix owner |
|---|---|---|---|---|
| **Z1 provider-structural** | OpenAI strict mode from the compiled artifact | wrong type, missing key, extra key, bad enum | API error / `refusal` / `incomplete` — **not** `definition_invalid` | provider/compiler |
| **Z2 canonical-schema value constraints** | In the strict artifact and *listed* as supported (`pattern` ×14, `minimum` ×30, `minLength` ×18, …), but enforcement strength is provider behavior; fine-tuned models drop them | ability score out of range, id string violating `pattern` | Pydantic `ValidationError` → `definition_invalid` (schema branch) | schema or prompt |
| **Z3 Pydantic-model invariants** | `@model_validator` on domain models (`profiles.py`, `primitives.py`) — **invisible to any JSON schema**, so structured outputs cannot know about them | cross-field profile consistency | Pydantic `ValidationError` → `definition_invalid` (schema branch) | contract design |
| **Z4 domain validation** | `validate_definition(…, generation_candidate)` receipt: derivations, duplicates, reference integrity | attack bonus not derivable, duplicate proficiency, dangling spell ref | `ValidationReceiptV1.invalid` → `definition_invalid` (domain branch) | prompt or model semantics |

Read correctly, the zones are diagnostic gold:

- **Z1 absence is evidence.** Under `strict: true`, schema-adherent output is the provider's job. If `definition_invalid` fires at all, the interesting cases are Z2–Z4.
- **A Z2/Z3-heavy failure pattern** means the compiled schema under-specifies what Pydantic enforces → tighten canonical constraints, or teach the prompt, or accept and document.
- **A Z4-heavy failure pattern** means the model doesn't understand statblock mechanics → prompt/semantics work, and *only then* the bounded-repair successor named in PR `#449`.
- Blind prompt tuning without the zone split is guessing — the reason `DMS-VAL-01` precedes any repair slice.

`DMS-VAL-01` packet guidance: `phase=schema_validation` covers Z2+Z3 (normalize `ValidationError` into bounded typed issues; preserve `loc` and `type` — they discriminate Z2 from Z3); `phase=domain_validation` carries the existing `ValidationIssueV1[]` packet. Raw provider payload retention stays banned.

---

## §6 Flexibility pressure points and design moves

Ordered by how often they will bite.

### 6.1 The all-required / null-union tax

Strict mode forces every property to be emitted; 55 optional sites must be explicit `null`s. On a 210-property schema the model spends reasoning and tokens deciding "null" dozens of times per generation, and every forced presence is a chance to hallucinate a value instead of a null.

**Moves:** prefer *grouped optional sub-objects* (one null collapses a subtree, e.g. `lair_profile: null` beats five nullable lair fields); treat the forced-null count as a schema-health metric; resist adding optional knobs to hot paths.

### 6.2 Union semantics: `oneOf` → `anyOf`, no discriminator keyword

`anyOf` admits payloads matching multiple branches; `discriminator` is stripped. The defense is **structural exclusivity**: every branch a closed object with a distinct required `const` tag (our 20 `const`s: `effect_type` / `mechanic_type` literals). With closed objects + distinct tags, cross-branch matches are impossible and `anyOf` is lossless in practice.

**Moves:** never add a union branch without a const tag; never rely on `discriminator` surviving compilation; keep Pydantic's smart-union matching as the server-side authority.

### 6.3 Conditional shapes are inexpressible

`if`/`then`/`else`, `dependentRequired`, `dependentSchemas` are banned. "Innate spellcasting requires per-day uses" cannot live in the schema.

**Moves:** express conditional truth in the domain validator (Z4), where it already lives; do not contort the schema with parallel object types to fake conditionals.

### 6.4 Metadata strip: semantics belong to the prompt

OpenAI *accepts* `description` hints (its own examples use them); PR13 strips them anyway — a conservative choice that moved ~14 KB of guidance out of the served schema. The system prompt (`"Return only the requested JSON schema instance."`) carries almost no field semantics, so the generation prompt builder is the only place meaning lives.

**Moves:** keep prompt builder colocated with the contract model; **candidate re-evaluation (not a fix):** selectively reintroduce high-value `description`s on mechanic/effect fields and measure token cost vs Z4 failure rate. This is a designed experiment, not a chat edit.

### 6.5 Key ordering is generation order

Structured Outputs emits keys in schema order. Identity-first ordering (`identity.name`, size/type before mechanics) lets the model commit to the creature concept before pricing mechanics — cheap quality lever.

### 6.6 Budget guards

We use ~4% of the property budget today. Rule-element growth is the pressure vector. **Proposed test:** CI guard failing when strict artifact exceeds, say, 25% of any OpenAI budget (properties, depth, enum count, string budget) — fail before the API 400s, not after.

### 6.7 The escape hatch: multi-pass generation

When a single schema gets too complex for reliable one-shot generation, the answer is **not** relaxing validation (explicitly rejected in PR `#449`) — it is splitting generation: identity/flavor pass → mechanics pass, each with its own smaller compiled strict schema, the second anchored to the first's durable draft identity. This composes with `DMS-VAL-01` (per-pass diagnostics) and with bounded repair (repair the failing pass, not the whole statblock).

### 6.8 API surface divergence (resolve or document)

Server provider (`openai_provider.py`) uses Chat Completions `response_format`; Buddy's `.cursor/rules/responses-api-structured-extraction.mdc` mandates Responses API `text.format` for extraction paths, with refusal/incomplete as first-class outcomes. Both enforce `strict` JSON Schema. New provider work should standardize on Responses API or this document must carry an explicit reason generation differs (reasoning-model support and outcome-shape parity argue for Responses).

---

## §7 Verification hooks

**Existing (Server, `tests/statblocks_v1/test_schema_snapshots.py`):** artifact↔model parity; metadata-vs-property-name preservation; closure + strip correctness; `anyOf`-not-`oneOf`; fail-closed on unsupported constructs; canonical/provider property-path parity.

**Proposed (not dispatched — fold into `DMS-VAL-01` or a schema-health slice):**

1. Budget-guard test (§6.6).
2. Strict↔canonical *validation-equivalence* audit: prove every constraint dropped in compilation (`default`, `description`, `examples`, `title`, `discriminator`) has zero validation effect — so Z2 is precisely enumerable.
3. Provider request-shape test asserting `strict: true`, schema name, and compiler fingerprint on every generation call (the Buddy rule already asserts this shape for extraction).
4. Fine-tune readiness marker: zone-2 constraint inventory test, so a future fine-tune knows exactly which constraints leave provider enforcement.

---

## §8 Checklist for the next complex contract

1. Pydantic model is the single source of truth; canonical + strict artifacts generated, checked in, staleness-tested.
2. Compiler rewrites are on the lossless list; everything else fails closed.
3. Unions: const-tagged, closed-object branches only.
4. Optionality: grouped sub-objects before scattered nullables.
5. Conditionals: domain validator, not schema.
6. `@model_validator` invariants listed in the contract's README — they are Z3, invisible to the provider.
7. Identity fields first in key order.
8. Diagnostics designed with the request (phase + bounded typed issues) — never bolted on after an opaque failure.
9. Responses API `text.format` with `strict: true` unless the divergence is documented.
10. Budgets measured in CI before the API measures them for you.

---

## §9 References

| Ref | What |
|---|---|
| `DungeonMindServer: statblocks_v1/domain/schema.py` | canonical/strict compile, fail-closed sets |
| `…/application/schema_compiler.py` | artifact load + staleness + closure assertion |
| `…/domain/schema_artifacts/` | the two checked-in artifacts |
| `…/infrastructure/openai_provider.py` | Chat Completions `response_format` provider |
| `…/application/generation.py` | the two `definition_invalid` branches |
| `…/domain/receipts.py` | `ValidationIssueV1` / `ValidationReceiptV1` (Z4 packet) |
| `…/domain/profiles.py`, `…/domain/primitives.py` | `@model_validator` Z3 invariants |
| Server branches `feat/statblocks-v1-pr13-contract-models`, `feat/statblocks-v1-pr16-generation`; commits `1c062b1`, `9b4d628`, `06a1f5f`, `0e34dd4` | prior art lineage |
| Buddy `.cursor/rules/responses-api-structured-extraction.mdc` | extraction-side strict-JSON rule |
| Buddy `apps/live_control_server/integrations/dungeonmind_statblocks/client.py` | `ErrorEnvelopeV1.error.details` already preserved at transport (dropped in orchestration — `BUDDY-VAL-01`) |
| PR `#449` | failure classification + `DMS-VAL-01` handoff |
| OpenAI Structured Outputs guide (fetched 2026-07-29) | §2 constraint matrix |
