# SERVER — exact Session 27 source review recovery

**Status:** ACTIVE, bounded file-restoration lease authorized by PRIME after the PR #966 deployment handback. This Buddy branch/PR head pins the operational handoff; a docs merge is not a prerequisite.

**Runtime:** `/home/drakosfire/.local/state/dungeonmindbuddy/runtime`, clean detached at `b9d9ff05eb7c7d6ae3fa8ab4c547cd55a7bbc710`. **Verified original:** `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`. **Independent audit:** DOGFOOD `dogfood-2026-10-06/source-recovery-audit.json` under its 2026-10-02 visualization workspace. Do not infer availability from a stored `exists` flag; check bytes and SHA-256 again before mutation.

**Primary question:** Can the existing ExtractionRun `084b3237-1fce-4a40-b8eb-eed7846a5bc4` regain exact read-only reviewability using its original SourceArtifact identity and byte-identical frozen components?

## Write lease

- In the permanent runtime only: `out/registries/source_artifacts.json` (currently absent; add only the verified `artifact:recap:longmont-c2:session-27:740dcd285ee5` record in the existing `dmb_source_artifact_registry_v1` schema); the run's two missing declared `repo://out/graph_memory/current_corpus_admission_acceptance_v1/execute-2026-09-16T020204Z-6e3b812a/extraction/session-27/084b3237-1fce-4a40-b8eb-eed7846a5bc4/{candidate_graph.json,source_span_index.json}`; and the existing `/home/drakosfire/.local/state/dungeonmindbuddy/runtime-artifact-inventory.json` if its current list schema admits exact path/SHA entries without replacement.
- Preserve the already present exact source Markdown and registered source-span index, all existing inventory entries, local operator profile/session files, managed World, committed Plan4 and pinned Run. Do not change any Git checkout, DB row, Graph revision, catalog/run state, source ID/URI/digest, or source prose. No extraction, provider call, prepare/confirm, admission, publication, or S28/S29 substitution.
- Wait until DOGFOOD's one approved live retrieval QC is finished before runtime file mutation. Stop if another writer owns any leased path, if bytes/digests/scope disagree, or if the source registry has become populated with conflicting identity. Preserve existing records if the registry appears during execution.

## Exact components

- `candidate_graph.json`: SHA-256 `f323a7464b301b507529923833d959ee044a8c9ca042ce38a082cc6769234d37`.
- `source_span_index.json`: SHA-256 `e4019b7492d00818f9b0ef24a7cfb782218cf7c638bc7cefb6d658556c14e0b7`.
- Source Markdown is already present in the runtime: SHA-256 `740dcd285ee5e630ad84e3b5617374b99126be1784e003dd02e7878fa013b4ad`.

## Acceptance witness

1. Record exact before-state: review-package GET is `422` for the existing run; registry absent; candidate/span files absent; original digests valid; Plan/Run and runtime inventory baselines captured.
2. Restore only byte-verified components and minimally register the exact existing SourceArtifact record. Add only the new exact path/SHA inventory entries. Verify destination bytes/digests and registry parser readback.
3. Repeat the exact run review-package GET. Pass only if it returns the legitimate review package with frozen source/candidate/span identity and evidence. If it reports another true blocker, record it without broadening this lease.
4. Compare Plan/Run metadata and all pre-existing inventory entries, keep checkout clean at the deployed SHA, and record how the restored files persist through the current deployment procedure. Report concrete evidence to PRIME. This is review restoration, not native Graph admission or a live answer acceptance claim.
