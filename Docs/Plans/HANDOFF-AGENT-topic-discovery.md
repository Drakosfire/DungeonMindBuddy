# AGENT — Discover topics beyond matched individuals

Status: ACTIVE. PRIME solo implementation under the Mirathorn lifecycle goal.
Base: Buddy main `d2d80adb6aace8d166c4619e3c377faf56870c90`.
Lane: `/tmp/prime-recap-mention-boundaries`, branch `codex/agent-topic-discovery`.
Topology: serial, one implementation PR. Current open Ingest/Plan/Play welcome
PRs and held MIND/Rules lanes are disjoint. The predecessor undated-source policy
is already present on accepted main; this slice transfers its policy-path lease.

## Outcome and evidence

An ordinary question about a category or practice should not treat a similarly
named individual as sufficient evidence. Prefer relevant admitted Graph knowledge
by using the existing unseeded topic search when initial matches fail to address
that question. Search results may expose source-backed descriptions attached to a
place or institution rather than a separately named topic node. Inspect relevant
returned assertions and open their passages when needed. Stop once sufficient.

The frozen `q_float_goat_transport` ordinary Build baseline answered accurately
from the saved source, but its two Graph operations followed Bubbles, an individual.
Read-only search on the same accepted native revision already returns the reviewed
livestock observation on `location:elderwyld` for “Float Goats” and “transport goods”.
This is a tool-choice hypothesis, not proof of general retrieval/extraction quality.
Private evidence: `experiments/build-governed-preview-20261016/` under Buddy's
local state, `float-goat-transport-*` and `float-topic-native-search-probe.json`.
No private examples or corpus facts enter production instructions or this PR.

## Exclusive write set

- `apps/live_control_server/services/agent_graph_policy.py`: generic harness-neutral
  topic-versus-individual retrieval guidance only.
- `Docs/Plans/HANDOFF-AGENT-topic-discovery.md`: this bounded contract/evidence.
- `Docs/Plans/HANDOFF-AGENT-undated-source-policy.md`: close the already accepted
  predecessor's implementation lease, preserving its evidence and limitations.

No tools, schema, scope, source visibility, evidence admission, identity merges,
retrieval implementation, provider route, authorization caps or runtime changes.
No source rewrite, extraction rerun, publication or retained state mutation.
The policy is shared by the existing Harness adapters; source authority stays
with DungeonMind. Category questions do not license inventing species nodes.

## Verification and rollout

Run actual existing shared-policy/Harness consumer tests, Ruff and cumulative diff
inspection. Do not add phrase-mirroring tests or claim prompt presence proves
behavior. Get independent ARCHITECTURE exact-head review and open the PR.
Only after acceptance may a newly pinned operational handoff deploy this policy
on PRIME's existing isolated8004/5207/privateAPP0025 preview with original source
roots and accepted nullable SDK. Repeat the frozen question as a changed-policy
experiment, preserving baseline, actual requests/results/answer, opened passages,
latency and token usage; no uncertain replay. Full saved source remains provided,
so success is ordinary topic discovery, not Graph-only reasoning. A prompt change
that fails to improve observed behavior is not semantic acceptance. DOGFOOD owns
5202 and operator UX inspection; those runtimes are outside this lease.
