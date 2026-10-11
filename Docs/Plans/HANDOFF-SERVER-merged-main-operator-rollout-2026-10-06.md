# SERVER — merged-main operator runtime rollout

## Artifact repository selection — 2026-10-11

**Status:** ACTIVE bounded implementation; awaiting PRIME review. This section
is a new configuration capability, separate from the completed rollout below.
PRIME authorized one serial Buddy PR on main
`20d0a4d79a4d3272f291f0fb56e71b73cbb82733`, branch
`codex/artifact-data-root`, isolated checkout
`/home/drakosfire/.codex/worktrees/buddy-artifact-data-root/DungeonMindBuddy`.
PRIME owns review/merge; DOGFOOD owns subsequent runtime deployment and one
prepare request. There is no graph confirmation or model-call lease.

The running current-main API resolves managed World `elderwyld` to native World
`eldyrwild`, but its exact C2S1 prepare failed `run_not_promotable` (422):
the file SourceArtifact registry was selected relative to the code checkout.
APP-STATE still resolves the exact run as reviewable and its source as available.
The unchanged registry, source body, frozen span index and candidate exist in
the retained primary data repository with their recorded SHA-256 hashes.

### Contract and exclusive write paths

`DMB_ARTIFACT_DATA_ROOT` selects the physical artifact **repository root**.
Unset retains each caller's existing root. A configured value must name an
absolute existing readable/searchable directory; empty, missing, relative,
unusable and escaped paths fail without falling back to the code repository.
Metadata/body/span/candidate reads agree on this base. APP-STATE remains the
canonical run/status/component authority; stored repo:// URI strings, IDs,
digests, source/run scope and semantic-review commitments do not change.

This root owns source registry/content/span files, frozen ingest components,
derived candidates, graph-ingest outputs and content-addressed promote seals.
It also owns the existing **file-backed** workspace registry, committed
worldbuilding Markdown and its file locks: normal workspace creation, Tiptap
prepare/commit, source creation and admitted span reads select the same owner.
The ordinary workspace writer produces that body; source admission does not
copy or synthesize it to hide a mismatched workspace owner.
PostgreSQL Plan/Run/content authority is unchanged.

Canonical components and output paths must remain inside the resolved artifact
root after symlink resolution. Missing registry/body/components and byte/scope
drift remain truthful failures. A fresh declared directory may receive new files
through existing authorized producers; selecting it does not adopt old runs.
Resolving a promotable run can create an immutable normalized-source seal in
`out/graph_memory/runs/promote_seals`; resolution is not entirely read-only.

`repo_root()`, Hermes dependencies under the code checkout's `out`, managed
World selection and World Graph storage configuration keep their own meaning.
`DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT` remains an extra byte-input allowlist.
`DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT` selects a confined subtree of the artifact
repository. Neither variable selects canonical source metadata authority.

Expected writes: `apps/live_control_server/config.py`; service modules
`source_artifact_registry`, `graph_run_registry`, `promotable_ingest_run`,
`extract_promote`, `graph_ingest_run_registry`, `graph_preview_runner`,
`recap_graph_preview_ingest`, `exact_run_evidence_correction`,
`recap_semantic_candidate_correction`, `workspace_document_registry`,
`tiptap_markdown_write`, `registry_file_lock`, `worldbuilding_source_span_read`;
the production extraction controller and graph-ingest packaging under
`src/graph_memory/extraction`; `tests/test_artifact_data_root.py`; this handoff.
Producer and workspace paths were added to the same lease after tracing their
physical outputs and shared lock domains. No dependency/pin changes, artifact
overlay, source authority migration, graph store or provider changes are included.

### Verification and deployment gate

Focused cohort: **219 passed, 2 deselected** using the unchanged pinned Core
`ba6069b91e1a608f125548860502a69b4c3e3fc6` source.
The split-root test uses actual registry/source/frozen index/candidate evidence
and a canonical run-port test double, verifies a literal source quote, and
reaches the native prepare boundary. It creates only the expected source seal.
Normal workspace author/commit/source/span flow, producer output roots,
confirm owner lookup and relocation rejection, digest/scope drift, traversal,
symlink escapes, invalid/missing roots and Hermes preservation are covered.
The canonical PostgreSQL run-port implementation is unchanged.

One existing selected-source-pin fixture fails identically on the exact base
because its synthetic native result lacks `objects`. The existing disposable
run-registry test could not start: dedicated PostgreSQL at 127.0.0.1:54329 refuses
connections. These are the two deselections; neither is claimed passing.
The first broader attempt used an older installed Core package and lacked
`SourceAnchorIndexRequest`; rerunning with the exact pin resolved those import
failures without editing dependency files. Pydantic field-shadow warnings carry.
Ruff has one pre-existing unused compatibility export in graph-ingest packaging;
the same import is present at the base. Other changed Python files pass Ruff,
and the cumulative diff passes whitespace checks.

After PRIME acceptance, DOGFOOD must deploy the accepted Buddy code under its
runtime lease and set the private operator configuration:

```text
DMB_ARTIFACT_DATA_ROOT=/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
```

Preflight must report effective code SHA/module path and resolved artifact root,
read the unchanged registry's exact source record, reload the canonical APP run,
and hash its three recorded components under the declared root. Do not call the
promotable resolver merely to claim a read-only preflight: it may write a seal.
Keep managed World `elderwyld`, native `eldyrwild`, campaign `longmont-c2`,
session `session-1`, and exact run
`7f205b79-54d4-40e5-a11c-61c512870b0a`.
Its candidate digest is
`f771a086f9f62072686957a0d1740363ad4237eed1b6a444a93f59e6c9160782`;
source revision is
`sha256:f1045adefbd67ec0943446bb17ab236388594d5d9dbfecb95646aa985e69c99b`.

Then make one prepare-only request through the running owning API, retain its
sealed current-parent package and source/collision evidence, and return it to
PRIME/human semantic review. Re-prove the 13 original raw-ID collisions and
existing object preservation with #1072 qualification; configuration must not
turn those IDs into overwrite authority. A live sealed package, source catalog
admission, deployment or semantic acceptance is not claimed by this PR.
Stop on changed bytes, run/status/scope/binding/head, path escape, required catalog
effects outside the C2S1 pair, or any need for graph confirmation/model calls.

Reviewed recap observation producer compatibility: pending source-proven
observation packages require the new internal binding validator/publisher from
`HANDOFF-BUDDY-reviewed-recap-source-observations.md`; a rollback to the #1073
publisher must not attempt to confirm those new packages. Already finalized
attributes remain readable through the existing Core observation facet. This
operation adds no Core migration, artifact-root setting or data-restore step.

## Completed 2026-10-06 rollout

**Status:** COMPLETE; runtime lease returned to PRIME on 2026-10-06. PRIME reviewed draft PR #978 at head `1c8c14c75f16a2bbe2ba3288e4ddd01c32a7b9db` and explicitly activated this bounded operational lease, conditional on every fresh preflight and stop condition below. The completed execution moved only the owned runtime to exact target `521a63518a1dd0188b76244c5382d8fb897878d4`.
**Source authority:** Buddy `origin/main@521a63518a1dd0188b76244c5382d8fb897878d4`, merge of accepted UI PR #972. The current runtime is clean and detached at #972 head `4722ac5b82b81970ef2a66eb21e28e9ee1f874fa`; `git diff 4722ac5b..521a6351` is empty. The target changes the deployed Git identity, not the source tree.
**Predecessor protocol:** completed [PR #966 operator deployment](HANDOFF-SERVER-pr966-operator-runtime-deploy-2026-10-06.md). Do not rewrite its historical settlement. PR #977's recap correction is draft and is outside this rollout target.
**Topology:** one operational rollout after PRIME releases all live QA/authoring leases. No source implementation or migration.

## Question and exclusive lease

Can the permanent local operator runtime move from the clean #972 preview checkout to exact merged `main@521a6351`, using the existing `nohup setsid ./run` lifecycle, while preserving the managed World, Plan, Run, Agent history, local sessions, source artifacts, and private profile?

Only the permanent checkout Git state and its `.run` launcher/PID/log files may change. Keep the checkout detached and clean. Do not run `git clean` or alter the stable `.venv`, UI dependencies, package/lockfiles, symlink targets, profile, credentials, data roots, databases, ignored `out/` artifacts, or application records. No model turn, Graph write, Plan authoring, S27 child/decision/prepare/confirm/publication, or live-answer acceptance test is part of this rollout. The managed World target-binding question remains separately with ARCHITECTURE and PRIME.

## Pinned environment to re-prove before activation

- Runtime checkout: `/home/drakosfire/.local/state/dungeonmindbuddy/runtime`; source `4722ac5b82b81970ef2a66eb21e28e9ee1f874fa`, target `521a63518a1dd0188b76244c5382d8fb897878d4`; no tree diff. Stop if remote `main` or the runtime checkout has changed without re-anchoring this handoff.
- Runtime `.venv` links to `.venv-stable` (Python 3.13.1). UI uses the bundled Node executable at `/home/drakosfire/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node` (v24.19.0); do not substitute the host's Node v18. `uv.lock` SHA-256 `932e0f3bcff556bbb445c897f1f9e85faaa9a5eea975802e283eefc05ebb0716`; `pyproject.toml` `e2c3eca37b33293ad1b4e468f0b644e6573b669de73d21c88025028d462c3d3b`; UI `package-lock.json` `860c764cbe376a7b996b77b6ee45f709f8debd9d4713de2f45dbf5817d87c5b2`. Do not sync or install dependencies in the permanent checkout.
- Launcher profile: `DMB_AGENT_GRAPH_LOCAL_PROFILE=/home/drakosfire/.local/state/dungeonmindbuddy/local-operator.env` (SHA-256 `af668792e1afc38a6c926736563f3ed309d205bbaca3212062708bc588a2a003`), `RUN_NO_RELOAD=1`, required World `elderwyld`. Runtime `.env` remains the symlink to the primary Buddy `.env` (target SHA-256 `f49f8232fc0536ac9366c798f811ec00d45fca43f82dadf68c4576f56f2c0bc0`); `.env.development` remains the OverMind symlink (target SHA-256 `ded1e088d0807ac0c1db32f1251abbf3485a4a52b5588381dc9c2559078aa1a8`). Never print their contents.
- Data roots: `DUNGEONMIND_SERVER_ROOT=/home/drakosfire/Projects/DungeonOverMind/DungeonMindServer` (observed clean at `26904d2b88d3da7f390cac5ad9dfd973e6d8e896`); `DMB_MANAGED_WORLD_DATA_ROOT=/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`; `DUNGEONMIND_LIVE_SESSION_DIR=/home/drakosfire/.local/state/dungeonmindbuddy/live-session`. Preserve `/home/drakosfire/.local/state/dungeonmindbuddy/local_graph_sessions.json` and `runtime-artifact-inventory.json`, including recovered exact S27 source/candidate/span artifacts.
- Owned launcher process group and listeners: profile ports UI 5202, Buddy API 8000, DungeonMindServer 7860. Planning observation: launcher PID/PGID 569891, UI 569919, API 569913, Server 569908; all three `/health` requests returned 200. Recheck PID ownership and process group at activation; never stop an unowned listener.

## Activation and acceptance witness

1. PRIME confirms independent source/review status and releases live QA/authoring leases. Before touching the runtime, fetch remote `main`; verify exact target commit/tree, clean detached runtime, profile and manifest hashes/symlinks, stable environments, owner PID group, 5202/8000/7860 health, and zero `agent.turn` rows with status `accepted` or `running`. Any mismatch pauses rollout for a new explicit target decision.
2. Capture a fresh read-only before snapshot of Plan/Run/history metadata and state-file digests. Use `content.work_object` (`kind='plan'`), `content.work_revision`, `content.working_copy`, `play.run`, `play.active_run`, `play.run_manifest`, `agent.conversation`, `agent.turn`, `agent.turn_reference`, and `plan_action.action`. Record row counts and canonical ordered metadata digests; exclude user text, Markdown, prompts, credentials, and session material from reports. Use stable primary-key order and the same selected metadata columns in both snapshots; encode rows with JSON `default=str`, `sort_keys=True`, and `separators=(',', ':')` before SHA-256. Hash local Graph sessions, runtime artifact inventory, and every live-session file by relative path plus file digest. Record exact Plan and active Run identities and current revisions without editing them.
3. Stop only the verified owned launcher group, move only the detached runtime checkout to target `521a6351`, then restart through the existing profile and `nohup setsid ./run` procedure. Do not run migrations, dependency sync, source extraction, or any writer. Stop if a port is taken by another group or preflight rejects the unchanged profile.
4. Verify clean detached target SHA, new owned PIDs, three health checks, exact profile/symlink/manifest hashes, local Graph profile and authorized read-only endpoint/session. Repeat the same Plan/Run/history and state-file snapshot. Pass only if counts, exact identities/revisions, canonical digests, active Run selection, Agent history, and private-file inventories match the fresh before snapshot. The new launcher/PIDs and Git SHA are the intended differences. Report the before/after evidence to PRIME and hand back the runtime; DOGFOOD's live answer QA is separate.

**Planning observation only (2026-10-06):** read-only APP-STATE counts were 6 Plans, 13 Plan revisions, 5 working copies, 4 Runs, 1 active Run, 4 Run manifests, 3 conversations, 7 turns, 20 turn references, and 7 Plan actions; zero accepted/running turns. The 25-file live-session inventory had SHA-256 `8c2e395539309431b7b608bf1c9c00e19a3f74a86540703e478fe0aece3ced4a`; local Graph sessions digest `fb597d0acc1228de481f5001798101899f7a793027be65e6692ecb3ad0af69b1`; runtime artifact inventory digest `304fb0d54c8c6e755d62e75ea0d3484eb42e3b7a83679de505e14b8cd454cbaa`. These are provisional observations, not a substitute for the fresh before/after comparison.

**Stop conditions:** changed target/main, dirty runtime or user work, mismatched environment/data hashes, active Agent turn, active QA lease, unknown PID/port owner, missing recovered S27 artifacts, preflight failure, any Plan/Run/history delta, or inability to prove read-only continuity. PRIME coordinated activation and review; this lease is now closed.

## Execution settlement

Immediately before the stop, remote `main` was still exact `521a63518a1dd0188b76244c5382d8fb897878d4`, runtime was clean detached at `4722ac5b82b81970ef2a66eb21e28e9ee1f874fa`, and the source trees matched. The fresh read-only snapshot matched the planning snapshot: zero accepted/running Agent turns or Plan actions, 6 Plans, 13 revisions, 5 working copies, 4 Runs, 1 active Run, 4 manifests, 3 conversations, 7 turns, 20 references, 7 Plan actions, and 25 live-session files. Profile, `.env` targets, lockfiles, local Graph sessions, runtime inventory, and exact S27 source/candidate/span hashes matched the pins. Authorized read-only Agent history returned HTTP 200. Old listeners were actual UI PID 569984, API PID 569921, Server PIDs 569916/569932, all in owned launcher PGID 569891.

The owned group received TERM and all three ports emptied. The runtime repository initially lacked the target Git object; `git fetch origin main` obtained exactly `521a6351` while the checkout remained at `4722ac5b`, with no file change. Detached checkout then moved cleanly to `521a6351`. Restart used the same profile/data roots and 5202/8000/7860 ports, the bundled Node 24 path, stable `.venv`, and `UV_NO_SYNC=1`; no dependency install or migration occurred. New launcher PID/PGID is **850119**; wrapper PIDs are UI **850184**, API **850179**, Server **850174**; actual listening descendants are UI **850206**, API **850187**, Server **850182/850198**. All are in the owned group. The launcher passed its built-in local Graph preflight and all three `/health` checks returned 200.

The post-restart read-only snapshot matched the fresh before snapshot exactly across all ten Plan/Run/history table counts and metadata digests, every listed profile/data/dependency/S27 file digest, symlink target, and the 25-file live-session inventory. Accepted/running Agent turns and Plan actions remained zero. Authorized read-only World conversation history returned HTTP 200 with schema `dmb_agent_conversation_history_v1`. The runtime is clean detached at exact `521a63518a1dd0188b76244c5382d8fb897878d4`; the Server checkout remained clean at `26904d2b88d3da7f390cac5ad9dfd973e6d8e896`. No model call, Graph write, Plan authoring, real S27 correction/decision/prepare/confirm/publication, or live answer acceptance occurred. PRIME owns any further QA or rollout action.
