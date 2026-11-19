# BUDDY — native managed projection by default

Status: ACTIVE. Owner/designer/implementer: MIND Elderwyld completion lane.
The operator explicitly owns and authorizes this lane's design, implementation,
review and merge decisions. No ARCHITECTURE coordination gate applies.
Topology: serial after accepted PR4104, merge
c6348aa1b4fbe3e62553724fb09baaf905662a0b. Actual base is that merge;
branch codex/v10-managed-native-projection in the existing task-owned Buddy checkout.

## One outcome and why

Every current managed Graph projection reads the bound generic-native KnowledgeSpace
without a per-World rollout selector or classic fallback. The existing active APP
binding, current native head or exact requested native revision, Core authorization,
source freshness and existing presentation mapper remain authority. This closes
one remaining V10 current-read selector; it does not deploy or finish V10/V11.

Source trace: project_managed_world_graph currently uses native support only when
DMB_VNEXT_MANAGED_PROJECTION_WORLD equals the managed World. Otherwise it calls the
classic project_world_graph. Native support and projection adapters already exist;
no new graph reconstruction, admission policy, bridge or converter is needed.

## Exact expected write lease and review map

- This handoff.
- Docs/Plans/HANDOFF-BUDDY-native-first-world-lifecycle.md: truthful completed4104
  settlement and compact current checkpoint, preserving references/proof limits.
- apps/live_control_server/services/managed_world_graph_projection.py: remove only
  selector/classic import/dispatch; retain source-identity/binding helpers and DTOs.
  Keep expected-binding checks before read and binding equality after read. Translate
  known native infrastructure/integrity failures through existing service errors
  without empty success, classic retry or exposing private internals.
- tests/test_managed_world_graph_projection.py: migrate old classic-dispatch mocks
  to the actual current boundary, preserving binding, query, pin and refusal checks.
- tests/test_native_graph_inspection.py: managed-projection owning cases and fixtures
  only; actual Core-backed reads, selector unset/stale and classic tripwires.

No route/auth/shared UI/type changes, dependency/Core/WK/migration/global configuration,
recap-context/harness migration, generic classic projection retirement or serving change.
No new test file or classification inventory edit. Checkpoint a genuinely coupled
scope expansion before absorbing it; user authority permits MIND to adopt a concrete
rebrief while preserving other active lanes' leases.

## Critique and invariants

Binding existence is not proof of a native head: missing/inactive/provisioning,
unconverted or corrupt state must fail closed. No fallback, auto-ingestion, guessed
IDs or alias-index authority. A pin must stay exact; never refresh a failed pin to
current head. Keep GM/hosted owner authentication at the existing route and its
post-serialization owner recheck. Current binding changes discard the result.

The current native branch can leak infrastructure exceptions to a generic500;
adopt explicit service503 for known unavailability and500 for persistence integrity,
while preserving existing missing-head/revision404 and binding409. Authorization
refusals must retain their status. No broad catch may manufacture an empty projection.
Preserve schema/DTO fields, ordering, aliases, direction, node-own versus adjacency
provenance, query presentation, source withdrawal and exact citation bytes.

Use two managed identities/native bindings with selectors unset or stale, real
Core records for positive integration, and classic tripwires. Prove current and
historical pins, denied/missing/corrupt authority, no mutation, changing bindings,
and the existing hosted/local owner fences. Reuse the native support service once
per projection and preserve its immutable parsed-cache/source-authority separation.

## Validation, dependencies and delivery

Core cf197b9939f7b9106c75a8afb9fcf918c8b4aa1c remains the locked runtime; no Core
PYTHONPATH overlay. No unmerged behavioral dependency. Current open PR3824/1868
patches were rechecked and do not touch the three owning code/test paths; remaining
open lanes were inspected for names/scopes. Shared hosted projection auth tests
remain read-only and run as regressions. No other lane is declared expired.

Run complete owning managed-projection and native-inspection modules and the
existing hosted-managed-projection regression. Run applicable exact-source backend
contracts plus the unmodified exact-head hosted frontend/build verifier, independent
cumulative review, expected-head merge and source-truthful settlement. No UI source
is planned; full discovered frontend is required if that scope changes. Preserve
inherited reds and proof limitations. The frozen classic retrieval benchmark is
not rerun. Final deployment/semantic/performance acceptance remains later work.

Resources: reuse /home/drakosfire/Projects/.codex/v7-elderwyld-scope and its verified
Projects UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8. Use owned scratch/cache and existing
admin32903 disposable fixture databases; never live54330/54331 or witness databases.
No new port/container/worktree, provider call or5202 rollout is authorized by this
slice's execution plan. Retain task evidence/workspaces for the full active goal;
cleanup requires resource/process/mount/DB-connection/dirty/unique-data checks and
specifically approved scope. No manual removals or reclaimed-byte claims.

## Implementation checkpoint

Draft PR4113 is open. The current service no longer reads the rollout selector
or imports/calls classic projection. Existing native support/presentation is the
only managed read path; missing authority cannot trigger conversion or fallback.
Availability/integrity errors map to service503/500 with safe messages; binding
and exact-pin error paths remain unchanged. Moved the existing parsed-cache import
to the import section; cache construction/lifetime is unchanged.

Working-tree diagnostics:17 owning managed-projection cases pass, including
provisioning/expected-binding refusal before Core IO and typed native failures.
Ruff and whitespace checks pass on the parent-owned service/test file. These unit
orchestration controls do not replace actual Core/HTTP proof. A test worker owns
only managed-projection cases/helpers in test_native_graph_inspection.py; two-space
source/WK publication fixture patterns already exist. Actual two-World/default,
authorized aliases, historical pins, citation bytes, withdrawal, auth, no mutation
and bounded work proof remain in progress. No Node/provider/serving change.
