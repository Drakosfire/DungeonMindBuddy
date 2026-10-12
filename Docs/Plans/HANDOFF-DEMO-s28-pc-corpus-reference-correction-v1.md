# HANDOFF — DEMO: reviewed PC corpus-reference correction

**Status:** BLOCKED — pending durable main landing and activation; no code lease yet
**Owner:** DEMO
**Authority base:** DungeonMindBuddy `origin/main@bb541a49085623a68a173acb46bf709248537c00`, 2026-10-11
**Proposed topology after activation:** parallel-independent from DOGFOOD chat stability/runtime, SERVER rollout preparation, and MIND source review
**Implementation branch:** `codex/demo-pc-corpus-reference-correction`
**Assigned PR:** `DEMO: audit PC corpus-reference correction`

## §1 One invariant

An operator can create one new, immutable, held recap-candidate child which changes only selected null `corpus_ref` fields to exact resolved PC references. Every attachment is supported by a reviewed source actor anchor, a pinned current party registry and carried roster, and a unique current native PC target in one pinned World/head. Replay, semantic decision, prepare, and native confirm reprove those bindings. A stale or ambiguous binding fails closed without minting a PC, aliasing an identity, changing canon, or publishing the held child.

This is a generic bounded correction operation. Session 28 supplies the motivating held parent, not hardcoded names or a runtime task. The original S28 extraction did not consume the later registry; record its use in the correction as a new reviewed basis.

## §2 Authority and inputs

- A private activation packet pins the held parent run, candidate, source, span index, current party registry, selected roster and native World/head. These exact identities stay outside this code-only PR.
- Select the greatest numeric roster at or before the target session as the carry-forward basis. No separate roster vote is implied.
- An attachment request names the exact parent revision, source and span hashes, registry bytes/hash, selected roster key, reviewed source actor anchors, candidate node IDs and null preimages, one World ID and expected native head, and unique active `pc:<slug>` targets of native `player_character` kind. The reviewer decision reference and reviewer identity are required before acceptance.
- The motivating real-case targets require source-backed semantic review under a separate data lease. Separately held or unresolved identities remain outside this operation.

## §3 Contract and refusal

The request is strict and typed: one to six unique node attachments, each with an exact `{type: "pc", ref_id: <slug>, resolution: "resolved"}` replacement. The parent must have exactly one matching node per ID and `corpus_ref: null`; its evidence must resolve to the pinned source/span and identify that actor. Registry membership and roster selection must match the exact pinned bytes and target slug. Native lookup must return exactly one active `pc:<slug>` in the requested World at the expected head, of `player_character` kind, without redirect or duplicate identity. Labels and fuzzy matching are never identity authority.

The child manifest and candidate digest bind all inputs, reviewer basis, and the exact replacement list. Replay changes only those `corpus_ref` fields and compares every other candidate byte semantically. Prepare and native confirm re-read parent/source/span/registry/native World/head and reject stale or foreign authority. A changed parent, source, roster, registry, World, head, target kind, redirect, duplicate, or unsupported actor must fail before a World mutation.

No provider call, extraction, live held-child creation, native publication, runtime switch, APP state change, PC mint, alias, or canonical identity write belongs to this implementation slice. Source-faithful temporary facts stay as session observations; this correction does not discard them wholesale.

## §4 Write lease and tests

Lease only the Buddy correction request/response model, recap correction service/replay, semantic basis and disposition verification, prepare/native-confirm checks, the owning route type, focused synthetic tests, and this handoff. Specifically:

- `apps/live_control_server/models/extract_promote.py`
- `apps/live_control_server/services/recap_semantic_candidate_correction.py`
- `apps/live_control_server/services/recap_semantic_disposition.py`
- `apps/live_control_server/services/extract_promote.py`
- `apps/live_control_server/routes/extract_promote.py`
- `src/application_state/ingest/service.py`
- focused tests under `tests/test_recap_semantic_candidate_correction.py` and relevant prepare/confirm tests
- this handoff

Use invented synthetic fixtures only. Prove exact child-only field delta and replay digest; accepted and rejected decision path; prepare and native-confirm revalidation; negative wrong registry/roster/source/parent/head/World/target kind/redirect/duplicate/mismatched ref/unsupported actor. Review the cumulative diff, then open the assigned PR. Return a new boundary question to PRIME rather than silently editing another owner's runtime, database, or schema.

## §5 Activation and current holds

Land this handoff on Buddy main and re-anchor open work before changing code. Once the exact base and path collision check remain valid, DEMO may mark the handoff ACTIVE in a guarded steward sync and start the assigned isolated lane.

The S28 held child remains held. MIND owns the independent actual-source/actor review. DOGFOOD owns the active chat-stability and runtime 5202 lane; SERVER owns oneAsk rollout preparation. No overlap in their code or runtime leases is authorized. A green synthetic PR does not activate the live six-PC correction or Session 29 integration.
