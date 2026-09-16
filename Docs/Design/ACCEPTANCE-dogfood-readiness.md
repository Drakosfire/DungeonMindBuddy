# Acceptance Doctrine — Dogfood Readiness

**Status:** ACTIVE product-acceptance authority  
**Adopted:** 2026-09-15  
**Applies to:** CON-READY / DOGFOOD-CONTINUITY and any capability described as ready, demo-ready, dogfood-ready, or production-usable  
**Repository:** `Drakosfire/DungeonMindBuddy`

## 1. Forcing rule

> **If the operator cannot dogfood it through the normal product, it is not ready.**

A structural, migration, publication, schema, or smoke-test PASS is necessary evidence for the boundary it tests. It never overrides a failed human/product dogfood gate.

The canonical distinction is:

```text
structural acceptance
  proves data/state can cross the tested machine boundary

product loadability
  proves the resulting product object can be opened and traversed through normal product reads

operator dogfoodability
  proves a human can select the right authority/context and use the result through the ordinary product

semantic usefulness
  proves the loaded information is correct/complete/useful enough for the intended questions and tasks

Agent usefulness
  proves the Agent can investigate and synthesize from the same product-visible authority
```

These are cumulative gates, not interchangeable labels.

## 2. Readiness ladder

### Gate A — Structural acceptance

Examples:

- exact source bytes were accepted;
- candidate/admission contracts held;
- governed writes committed immutable revisions;
- parent/head continuity was preserved;
- reload/restart preserved durable state.

A PASS here means only that the tested structural contract is true.

It does **not** establish that the output is readable, semantically correct, useful to a GM, or usable by the Agent.

### Gate B — Product loadability / addressability

Anything represented as a published/admitted product object must be usable through the same normal product read contracts that surfaces and Agent tools consume.

For a published World object, the minimum round-trip invariant is:

```text
projection/search exposes durable object identity X
        ↓
exact-object(X) resolves the same object
        ↓
complete-object(X) resolves the same object
        ↓
neighborhood/evidence operations that target X do not treat X as missing
        ↓
source/evidence navigation remains bound to the same World/campaign/revision
```

An object present only in a raw publication payload, contribution, database row, diagnostic dump, or Graph Review candidate/admission record is **not product-loadable** if ordinary product reads cannot open it.

Identity remapping is allowed only when it is durable, explicit, and round-trippable. A producer may not expose one identity while consumers silently require another.

### Gate C — Operator dogfoodability

A human operator must be able to reach the tested World/campaign/revision through ordinary product affordances and perform the representative workflow without reconstructing internal IDs, editing environment state between actions, or dropping to database/terminal inspection as the primary interaction path.

Terminal/bootstrap work may be necessary to start a local development stack. It does not count as the product interaction itself.

Examples of a failed operator gate:

- the UI silently opens the wrong World;
- campaign/focus selection cannot express the intended campaign union/lens;
- an object is visible but cannot be opened;
- source/evidence links dead-end;
- a normal surface cannot target the accepted authority without ad-hoc request crafting.

Any such failure keeps `dogfood_ready = false` even when Gate A passed.

### Gate D — Semantic usefulness

Once the product can actually load and traverse the accepted authority, evaluate whether it contains enough source-grounded truth to answer the intended questions.

Separate at least:

```text
coverage / recall
identity + connectivity
source / temporal / planning authority
bounded inference
synthesis quality
```

Do not use a product-loadability defect as evidence that the source fact was never extracted, and do not use raw database presence to excuse a product retrieval miss.

### Gate E — Agent usefulness

Agent evaluation begins only after the same graph/retrieval path is loadable enough for an oracle/operator to use.

The Agent must consume the normal governed product context/tools. A direct corpus/database fallback that the ordinary product does not expose invalidates the dogfood claim.

Compare:

```text
oracle/operator answerable
vs
Agent answerable
```

A zero-tool abstention on an oracle-answerable question is an Agent/tool-orchestration failure, not a graph-coverage success.

## 3. Acceptance labels

Use scoped labels rather than one overloaded PASS:

```text
STRUCTURAL ACCEPTANCE = PASS | HOLD
PRODUCT LOADABILITY = PASS | NOT_READY | HOLD
OPERATOR DOGFOOD = PASS | NOT_READY | HOLD
SEMANTIC COVERAGE = measured result | NOT_MEASURED
AGENT ANSWERABILITY = measured result | NOT_MEASURED
SEMANTIC MODEL SELECTION = HOLD until a separate comparison earns it
```

A higher layer may not be labeled PASS merely because a lower layer passed.

`READY`, `DEMO_READY`, and `DOGFOOD_READY` require all lower gates that the claimed workflow depends on.

## 4. Evidence precedence

When evidence disagrees:

```text
human/product dogfood failure
    outranks
structural smoke for a broader readiness claim
```

This does not invalidate the structural test. It narrows what that test proved.

Example:

```text
44 chronological governed writes complete with exact head continuity
→ STRUCTURAL ACCEPTANCE = PASS

accepted object cannot be opened through product retrieval
→ PRODUCT LOADABILITY = NOT_READY
→ DOGFOOD_READY = false
```

Both statements are simultaneously true.

## 5. Repair sequencing after a dogfood STOP

Repair the earliest failed boundary first.

```text
structural write failure
  → repair structural producer/write boundary

published object exists but cannot be opened
  → repair publication/read identity continuity before semantic or Agent tuning

operator cannot select/mount correct authority
  → repair product mounting/context UX before claiming human dogfood

oracle cannot answer from loadable graph
  → repair graph coverage/connectivity/authority

oracle can answer but Agent cannot
  → repair Agent retrieval/orchestration/synthesis
```

Do not tune a downstream layer to compensate for an upstream failure.

## 6. Anti-shortcuts

The following do not satisfy dogfood readiness:

- reading PostgreSQL directly instead of using product reads;
- inspecting raw publication payloads instead of opening the published object;
- using repository/Markdown search to rescue a graph miss;
- hard-coding an evaluator-only ID translation;
- changing the benchmark question to match what the product can answer;
- adding an Agent-only fallback unavailable to the operator;
- treating HTTP 200 as useful Agent behavior when the Agent did not investigate or answer;
- treating a UI render as success when it is bound to the wrong World/campaign/revision;
- relabeling a structural PASS as dogfood PASS.

## 7. Current accepted lesson

The current-corpus acceptance work demonstrated the distinction directly:

```text
structural current-corpus acceptance
  PASS

follow-on accepted-World question gauntlet
  dogfood_ready = false
```

The observed blockers include published-object read continuity, Agent non-investigation on oracle-answerable questions, and product World/campaign mounting mismatches. Those are not reasons to weaken the dogfood gate; they are the work the gate was designed to expose.

Future handoffs and reports must preserve this distinction explicitly.