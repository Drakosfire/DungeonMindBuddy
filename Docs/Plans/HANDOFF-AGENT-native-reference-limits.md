# AGENT: preserve native evidence and claim identifiers

Status ACTIVE under PRIME's Mirathorn lifecycle goal. Base
`2e61446033eac508233a94cfb523c62d42d622ad`; serial successor to accepted #1217.
PRIME implements solo; ARCHITECTURE independently reviews.
Lane `codex/agent-native-reference-limits`, `/tmp/prime-recap-mention-boundaries`.

## Outcome and evidence

Ordinary Build's native selected-source index currently fails before provider
admission: 67 selected evidence IDs exceed APP's 256-character source-pin bound.
Read-only full retained snapshot at `rev:d87693281c3f4cd17861139771ea0c31`
contains 108 evidence IDs above 256 (maximum 268), assertion IDs up to 129 and
relationship IDs up to 177. Native EvidenceRef contracts require nonblank strings
without a declared maximum; evidence construction composes artifact and span IDs
(`evidence:{artifact_id}:{span}`), so 256 is not a native identity invariant.
No private identifier values belong in this handoff or tests.

Define explicit Buddy consumer limits: evidence reference IDs 1024 characters,
claim labels 256 characters (models commonly reuse assertion/relationship IDs).
These are bounded consumer envelopes with headroom over observed composite IDs,
not claimed native parity. Keep source artifact/revision, anchor, object, World,
route, request/call and provider identifiers at their existing limits unless an
owning test proves this same path needs another change; return to PRIME first.

Preserve exact bytes through selected index, source authorization, source-read
receipt, protected passage trace, source-open API target and fresh APP readback.
No hashing, truncation, alias, rewrite or republication. Existing receipt/digest
semantics stay unchanged. Count/aggregate payload and trace bounds remain in force.
SQL stores these identities in JSON with aggregate limits, not individual ID
length constraints; verify against current migrations before declaring no schema
change. UI already treats evidence/claim strings as opaque, with no per-ID cap.
Harness authoritative retrieval payloads remain complete JSON; its boundedIds
telemetry is non-authoritative and outside this representation repair.

## Exclusive write lease

- This handoff.
- `Docs/Plans/HANDOFF-AGENT-build-governed-conversation.md` (sync accepted code and link pinned preview contract).
- `src/application_state/agent_conversation/identifier_limits.py` (new shared constants).
- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/context_trace.py`
- `apps/live_control_server/models/agent_turn.py`
- `tests/test_agent_build_governed_graph.py` (native-shaped long-reference owning witness).
- `tests/application_state/test_graph_identifier_limits.py` (new boundary/serialization/limits tests).

No active open-PR overlap was found. No serving, source, Graph publication,
provider inference, dependency or migration edits in implementation. The owned
5207/8004 preview stays on accepted #1217 and its verified APP clone until this
fix is independently accepted. 5202/5876 and operator work remain untouched.

## Verification

Long native-shaped evidence (>256) and claim (>128) must survive the real APP
provider/broker/read/trace/history/source-target path byte-for-byte. Test exact
boundary acceptance and over-limit rejection before provider admission, mutated
identity/digest rejection, old shorter Plan/Build replay and aggregate limits.
Inspect cumulative diff, open one PR, obtain independent exact-head review.
After acceptance, the actual read-only Mirathorn resolver must pass before a
fresh ordinary Agent question. No replay of uncertain attempts.

## Review evidence

44 owning tests pass: long native-shaped IDs through real APP provider admission,
Graph/source broker, producing citation, protected trace, fresh-service history
and source-open target; short/268/boundary source codecs; claim labels through
256; over-limit refusal before provider admission; altered producing evidence
refusal; unchanged Build ledger and protected-trace aggregate limits. No SQL
per-ID evidence/claim length constraint exists in current migrations; storage
remains JSON under the existing aggregate limits, so no migration is required.
Existing source/World identity and digest checks are unchanged.
Log `/tmp/graph-reference-limits-tests.log`. Ruff and cumulative diff checks pass.
No provider inference, source write, native publication, retained migration or
serving replacement occurred. Actual resolver/ordinary-answer acceptance is next.
