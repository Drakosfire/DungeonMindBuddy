# HANDOFF: Phase B — canonical route-equivalence artifact output and byte-stable regression

**Date:** 2026-05-10  
**Status:** Ready for execution by a single subagent.  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (Phase 2 / M2).  
**Checklist anchor:** `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` (Phase B).  
**Replaces:** `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-phase-a-gate-close-and-route-id-validation.md` (retired).

---

## 1. Mission (one sentence)

Add a deterministic CLI driver that writes `RouteEquivalenceRecord` JSONL artifacts for **Campaign 1** and **Campaign 2** registries to a canonical directory, and prove byte-stability with a regression test that compares stored artifacts against a fresh build.

## 2. Required model

- **Model:** `composer-2` (mechanical fix; design is settled).
- **Subagent type:** `generalPurpose` or the project's preferred composer-2 wrapper.

## 3. Authoritative inputs the subagent must read first (in this order)

1. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — Phase 2 section, `execution_state`, and the M2 row in milestone exit criteria.
2. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — Phase B section, current Reanchor Block.
3. `src/lexicon_phase_b/__init__.py`
4. `src/lexicon_phase_b/route_equivalence_manifest.py` — note the existing `build_route_equivalence_manifest` and `write_route_equivalence_manifest` and that the writer **already** sorts records by `record_id` and writes JSONL.
5. `src/lexicon_phase_b/schemas.py`
6. `tests/lexicon_phase_b/test_route_equivalence_manifest.py` — existing test conventions.
7. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json` — registry input #1.
8. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json` — registry input #2.
9. `evals/sentence_routing_retrieval_falsification/artifacts/.gitignore` — confirm what is and is not committed under that artifacts tree.
10. `evals/sentence_routing_retrieval_falsification/README.md` — section that mentions `artifacts/lexicon/benchmark_lexicon_seeds_v1.json` (this is the precedent for committing a small lexicon JSON in this folder; the new artifacts follow the same pattern).

## 4. Files in scope (allowlist — touch nothing else)

The subagent **must** confine its `git diff --stat` to exactly these paths:

| Action | Path |
|--------|------|
| **Create** | `scripts/build_route_equivalence_manifests.py` |
| **Create** | `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl` |
| **Create** | `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl` |
| **Create** | `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py` |
| **Modify (append-only)** | `evals/sentence_routing_retrieval_falsification/README.md` (add a short section under the existing lexicon paragraph; do not restructure other sections) |
| **Modify (status update only)** | `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` (check off the two Phase B items the work closes; append a session log entry) |

## 5. Files explicitly OUT OF SCOPE (do not touch)

- `src/lexicon_phase_b/*` — schemas and builder are stable on `main`. **Do not refactor.**
- `tests/lexicon_phase_b/test_route_equivalence_manifest.py` and the other three lexicon test files. **Do not edit existing tests.**
- Any file under `tests/test_token_resolution_*` or `tests/test_benchmark_lexicon_seeds*`.
- Any file under `evals/sentence_routing_retrieval_falsification/gold/` (gold edits are not in scope; the C1S13 content concern is captured separately in `Backlog.md`).
- Any file under `corpus/` (registries are inputs, not edited here).
- Any other `.cursor/`, `Docs/Design/`, or unrelated handoff/report files.
- Adding any new dependency to `pyproject.toml` / `uv.lock`. The CLI uses only the standard library and the existing `src/lexicon_phase_b/`.

If a file outside the allowlist looks like it needs a tiny touch, **stop and report** in the final output — do not silently expand scope.

## 6. Concrete implementation contract

### 6.1 New CLI: `scripts/build_route_equivalence_manifests.py`

Behavior:

- **Default registries:** discover both committed registries by exact path (do not glob `**`):
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json`
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json`
- **Default output directory:** `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/`
- **Default output filenames:** `route_equivalence_longmont_c1_v1.jsonl` and `route_equivalence_longmont_c2_v1.jsonl`. Pattern: `route_equivalence_<campaign_id>_v1.jsonl` where `campaign_id` is the value `_normalize_campaign_id` returns (`longmont-c1` etc., lowercased and underscored).
- **Reuse, do not reimplement:**
  - `from src.lexicon_phase_b.route_equivalence_manifest import build_route_equivalence_manifest, write_route_equivalence_manifest`
  - Do **not** open the registry JSON or write JSONL by hand. The writer already sorts records and writes deterministic JSONL; rely on it.
- **Modes (argparse):**
  - `--write` (default if no mode is given): build and overwrite the canonical files at the default output paths.
  - `--check`: build to a temp directory, compare bytes against the canonical committed files, and exit non-zero on any mismatch with a one-line summary per mismatching file.
  - `--out-dir PATH` (optional): override default output directory (used by tests).
- **Exit codes:** `0` success, `1` byte mismatch in `--check`, `2` argparse / IO error.
- **Stdout (success):** one line per artifact, e.g.  
  `wrote evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl (N records)`  
  In `--check` mode print `OK <path>` per matching file, `MISMATCH <path>` per failing file.
- **No prints of registry contents or PII.** The CLI must not log NPC names, slugs, or hub paths beyond what `write_route_equivalence_manifest` already serializes into the artifact.
- **No env vars, no config files, no MCP / network.** Pure local IO over allowlisted paths.

### 6.2 New committed artifacts

- Run the CLI in `--write` mode against `main` once, on a clean checkout, producing the two canonical files listed above.
- Each line is one `RouteEquivalenceRecord.model_dump(mode="json")` JSON object, sorted by `record_id`. The writer guarantees this; do not reimplement.
- Confirm both files end with a single newline and no trailing blank line (the writer's behavior).
- Commit the artifacts. They are small JSONL files and serve as the byte-stable golden output for the regression test.

### 6.3 New regression test: `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`

Test cases (one test function each, parametrize across `(campaign_id, registry_path, expected_artifact_path)`):

1. **Build matches committed artifact byte-for-byte.**
   - Call `build_route_equivalence_manifest(registry_path)` then `write_route_equivalence_manifest(records, tmp_path / "out.jsonl")`.
   - Read `tmp_path / "out.jsonl"` bytes and the committed artifact bytes; assert equality.
2. **Determinism within a process.**
   - Build twice in the same test, write to two different tmp paths, assert byte equality.
3. **Schema-version pin.**
   - Open the committed artifact, decode the first non-empty line as JSON, assert `schema_version == "0.2.0"` and `authority_effect == "routing_only"`. This pins the contract surface so a silent bump of either field fails CI loudly.

The test must use only `pathlib`, `json`, and `pytest`. No subprocess. No shelling out to the new CLI (the CLI is exercised by the operator runbook command in §7.3, not by pytest, to keep the test suite hermetic).

### 6.4 README touch

Append (do not rewrite) a short subsection under the existing paragraph that mentions `benchmark_lexicon_seeds_v1.json` in `evals/sentence_routing_retrieval_falsification/README.md`. Suggested heading: `Route equivalence manifests (Phase B)`. Two to four short paragraphs, no examples copy-pasted from corpus content. State:

- Output directory.
- Filename pattern (`route_equivalence_<campaign_id>_v1.jsonl`).
- Builder source: `src/lexicon_phase_b/route_equivalence_manifest.py`.
- Operator command: `uv run python scripts/build_route_equivalence_manifests.py --check` (CI-style) or `--write` (rebuild).
- Determinism guarantee + the test path that enforces it.

### 6.5 Checklist updates

In `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`, **only**:

- Mark these two Phase B rows checked:
  - `Generation is deterministic for fixed inputs (byte-stable output)` -> `[x]` with evidence: test path + commit-time command output excerpt.
  - `Artifact output path standardized and documented` -> `[x]` with evidence: directory path + README anchor.
- Append a new dated session log entry at the **top** of the session-log list following the existing newest-first style. Phase moved: `stayed B`. What turned green: byte-stable artifacts under canonical path + regression test. What stayed red: nothing for these two items; remaining Phase B work is the schema/generator coverage for non-route artifacts (entity candidates, lexical handles), captured separately in the super-plan. Next single action: stand up entity-candidate / lexical-handle deterministic generators (next handoff).
- Do **not** change the active phase, the Reanchor Block, or any unrelated checklist row.

## 7. Verification commands (subagent must run all and paste outputs verbatim in the report)

Run from the repo root with a clean working tree on the working branch.

### 7.1 Build artifacts

```bash
uv run python scripts/build_route_equivalence_manifests.py --write
```

Pass condition: exit code `0`; two `wrote …` lines printed; both target files updated on disk.

### 7.2 Byte-stable check

```bash
uv run python scripts/build_route_equivalence_manifests.py --check
```

Pass condition: exit code `0`; two `OK …` lines printed; **no** `MISMATCH` line.

### 7.3 Test suite

```bash
uv run pytest tests/lexicon_phase_b/ -q
```

Pass condition: exit code `0`; new `test_route_equivalence_artifacts_byte_stable.py` collected; total count is the existing count plus the new tests; **all passed**.

### 7.4 Token-resolution regression guard (must not break)

```bash
uv run pytest tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q
```

Pass condition: exit code `0`. The work in scope must not affect these.

### 7.5 Phase A audit must remain green

```bash
uv run python scripts/audit_world_campaign_alignment.py
```

Pass condition: exit code `0`; output begins with `World/Campaign alignment audit: PASS`.

### 7.6 Diff scope sanity

```bash
git diff --stat -- \
  scripts/build_route_equivalence_manifests.py \
  evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl \
  evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl \
  tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py \
  evals/sentence_routing_retrieval_falsification/README.md \
  Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md
```

Pass condition: this is the **only** non-empty `git status` and `git diff --stat` surface. If `git status` shows any other modified or untracked file, **stop and report**, do not commit.

## 8. Acceptance criteria (all must be true before reporting completion)

- §7.1, §7.2, §7.3, §7.4, §7.5, §7.6 all pass.
- The two new JSONL artifacts exist at the canonical paths and contain at least one record each (the registries are non-empty).
- The new test file imports only `json`, `pathlib`, and `pytest` (no subprocess, no network).
- `git diff --stat HEAD` is limited to the six allowlisted paths in §4.
- No new entries appear in `pyproject.toml`, `uv.lock`, or any other dependency file.
- No file under `src/lexicon_phase_b/`, `tests/lexicon_phase_b/test_route_equivalence_*` (existing), `tests/test_token_resolution_*`, `tests/test_benchmark_lexicon_seeds.py`, or `corpus/` is changed.

## 9. Reporting contract — paste this completion report verbatim into the final reply

The subagent must finish with a single completion report. Do not paraphrase the operator-facing reply; the operator needs the exact fields below to verify acceptance without re-running anything.

```
## Phase B canonical artifact output — completion report

### Diff scope
<paste output of `git status --porcelain` here, exactly as printed>
<paste output of the §7.6 `git diff --stat -- …` command here>

### Verification command outputs

#### §7.1 build
$ uv run python scripts/build_route_equivalence_manifests.py --write
<exact stdout>
exit_code: <integer>

#### §7.2 check
$ uv run python scripts/build_route_equivalence_manifests.py --check
<exact stdout>
exit_code: <integer>

#### §7.3 lexicon tests
$ uv run pytest tests/lexicon_phase_b/ -q
<final summary line, e.g. "N passed in 0.0Xs">
exit_code: <integer>

#### §7.4 token-resolution regression guard
$ uv run pytest tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q
<final summary line>
exit_code: <integer>

#### §7.5 audit
$ uv run python scripts/audit_world_campaign_alignment.py
<exact stdout>
exit_code: <integer>

### Artifact metadata
- route_equivalence_longmont_c1_v1.jsonl: <byte size>, <line count>, sha256 <hex>
- route_equivalence_longmont_c2_v1.jsonl: <byte size>, <line count>, sha256 <hex>

### Schema pin sample
First record from route_equivalence_longmont_c1_v1.jsonl (decoded JSON, single line):
<paste the JSON object>

### Out-of-scope drift check
- pyproject.toml unchanged: <yes/no>
- uv.lock unchanged: <yes/no>
- any src/lexicon_phase_b/ changes: <none/list>
- any corpus/ changes: <none/list>

### Acceptance verdict
- All acceptance criteria in §8 satisfied: <yes/no>
- If no: <one paragraph explaining what blocked completion and what was deliberately left undone>
```

## 10. Stop-and-report triggers (do not push through)

The subagent must halt and report — without committing — if any of these occur:

- A registry file is missing or fails to parse.
- `build_route_equivalence_manifest` raises for any reason.
- `--check` reports `MISMATCH` after a `--write` round-trip on the same checkout (would indicate non-determinism in the writer or schema; that is out of scope for this handoff and must escalate).
- `tests/lexicon_phase_b/` count drops vs the pre-handoff baseline (existing tests must keep passing as-is).
- `git status` shows any file outside §4.

In any of those cases, the completion report's `Acceptance verdict` is `no`, with the specific trigger called out under "what blocked completion." Do not attempt a workaround.

## 11. Out of scope (parking lot)

These are explicitly **not** part of this handoff. Any of them is a separate, future handoff:

- Entity-candidate or lexical-handle artifact generators (Phase B remainder).
- Wiring artifacts into the retriever or canvases (Phase 4 / Phase 5).
- C1S13 hierarchy content audit (`Backlog.md` `[IDEA] C1S13 hierarchy content audit`).
- Any change to `RouteEquivalenceRecord` schema or `entity_kind` semantics.
- Adding an `out/` writer for incremental builds, manifest hashes alongside JSONL, or compression.

If the subagent believes one of these is necessary to complete §8, that is a sign the brief is misunderstood — stop and report instead of acting.
