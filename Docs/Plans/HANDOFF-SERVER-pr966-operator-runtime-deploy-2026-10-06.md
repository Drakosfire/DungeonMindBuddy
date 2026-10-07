# SERVER — PR #966 operator runtime deployment

**Status:** COMPLETE; operator deployment lease released. PRIME authorized the coordinated restart and owns review. This handoff is pinned by its branch/PR head and did not need to merge before execution.

**Source authority:** Buddy `main` merge `b9d9ff05eb7c7d6ae3fa8ab4c547cd55a7bbc710` for PR #966. Deploy that exact commit to the clean detached checkout at `/home/drakosfire/.local/state/dungeonmindbuddy/runtime`. Predecessor operator checkout: `1d558057ebc40711f745e30d9f07a0db6fe8ba70`.

**Primary question:** Can the permanent local operator runtime adopt the merged selected-Plan Graph retrieval repair while preserving existing authority, state, and daemon lifecycle?

## Lease and invariants

- Mutate only the permanent runtime checkout's Git code state and its `.run` launcher/PID/log files. Keep the checkout detached and clean at the exact merged commit. Use the existing stable `.venv` and UI dependencies; no migration, lockfile, profile, or data-root rewrite.
- Preserve `/home/drakosfire/.local/state/dungeonmindbuddy/local-operator.env`, local Graph sessions, `live-session` profiles/history, and the primary managed-World data root. Preserve the current committed Plan4 and pinned Run in the application database. Do not delete, recreate, or replace any existing record.
- Use the existing `nohup setsid ./run` launcher lifecycle and ports 5202/8000/7860. Preserve the launcher profile values and private credential without printing it. No model turn, Graph write, Plan authoring, or live answer acceptance test during this deployment.
- Stop only after DEMO and DOGFOOD hold authoring/model activity and a fresh database check shows no accepted/running Agent turn. If the runtime checkout is dirty, profile or state paths changed, a port is owned by a different process group, or the target commit is unavailable, stop and report the smallest blocker.

## Acceptance witness

1. Before restart record exact old checkout and launcher/listener PIDs; verify clean detached Git, expected symlinks, three port health checks, local session count, state-file digests, and no accepted/running turn.
2. Stop the owned launcher group cleanly. Move only the runtime checkout to the exact merged commit. Restart with the existing profile via detached `nohup setsid` lifecycle; retain 5202/8000/7860.
3. Verify clean detached deployed SHA, new launcher/listener PIDs, UI/API/DungeonMindServer health, unchanged private profile and preserved live-session data. Verify the local Graph profile and an authorized read-only endpoint/session remain available. Compare database Plan/Run presence before and after without mutations.
4. Report the exact deployed revision, PIDs, checks, and any limitation to PRIME and hand the runtime back to DOGFOOD for its separately authorized live selected-Plan retrieval QC. Backend tests alone do not establish a live Graph-backed answer.

**Implementation evidence before deployment:** PR #966 corrected head `c6b10d92937f092299897f8a25c9cd7af6931360` merged as the source authority above. Its six-path cumulative diff passed owning PostgreSQL tests (68), targeted Ruff, and diff check. DOGFOOD separately verified the parser/helper against current Plan Options.

**Deployment settlement:** The permanent checkout is clean and detached at exact `b9d9ff05eb7c7d6ae3fa8ab4c547cd55a7bbc710`; 5202/8000/7860 health checks passed with launcher PID 569891, preserved Node 24/stable venv/live-session profile, active local session, authorized read, and unchanged pre-restart Plan/Run and live-file baselines. DOGFOOD received runtime handback for its separate live answer QC; no live Graph-backed answer acceptance is claimed here.
