# INGEST: source-faithful recap extraction prompts

Status: ACTIVE — explicitly directed by PRIME on 2026-10-17 after DOGFOOD's exact-run Session 29 source/gold audit.

Base: `origin/main@541a8201405eb231f136a19963dc89b22d92f1b0`.
Branch: `codex/ingest-recap-source-faithfulness`.
Checkout: existing `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`; the shared Git metadata is read-only in this sandbox, so the PR branch is created from the verified GitHub main ref and this checkout is used only for the leased source files and tests.
Topology: one serial INGEST implementation PR. DOGFOOD implements; PRIME owns coordination and merge; ARCHITECTURE independently reviews the exact cumulative diff.

## Capability and invariant

Make recap extraction prompts preserve distinctions already present in source prose. A structurally valid candidate must not turn intent into an event, collapse similarly named people, omit meaningful informal populations, merge separately named places, or bind a broad plural reference to a narrower entity without evidence.

The private Session 29 run and comparison with accepted gold motivate these general rules. Private source and model output remain in the local experiment directory; no corpus-specific names, quotes, manually patched candidate, or gold changes enter this PR.

The recap-only prompt guidance must require the extractor to:

- preserve modality, time, and attribution: planned, intended, proposed, possible, or reported actions remain distinct from actions that occurred;
- keep entities separate unless the source establishes their identity, and avoid resolving similar names through spelling or possessive similarity;
- retain source-mentioned informal groups or populations when they act as meaningful participants, while adding no unstated membership or identity;
- represent distinct source-named places/buildings separately when the prose treats them as distinct, rather than storing a compound location label;
- resolve broad plurals and event participants only to the specificity supported by the source; relationship evidence must support the relationship itself.

These rules are profile instructions, not new node kinds, schemas, or validation guarantees. The PR must not claim that prompt tests prove model semantic compliance. The current `recap_category_v1@1.0` identifier remains unchanged because the run service pins that profile version in its typed API; changing that serialized contract is out of scope.

## Exact exclusive write set

- `Docs/Plans/HANDOFF-INGEST-recap-source-faithfulness.md` — this pinned authority and evidence.
- `src/graph_memory/extraction/recap_extraction_profile.py` — recap-only guidance for the actor, location, collective, beat, encounter, and edge pass specs.
- `tests/test_recap_source_faithfulness_profile.py` — synthetic source/gold expectations exercised through the owning recap prompt builder.

No other paths are leased. In particular, do not change the category runner/consolidator, shared evidence rules used by Worldbuilding, native vocabulary, schemas, graph review, UI, server routes, or existing gold. The two other ACTIVE Ingest handoffs own disjoint server and gold paths. Uncommitted Ingest UI and persistence files already in the checkout are outside this lease and must remain untouched.

## Verification and limits

Run the focused new profile/prompt tests plus the existing extraction-profile and category-extractor tests; run `git diff --check`. Inspect the exact cumulative base→head diff against this allowlist. The test fixture must use synthetic prose covering intent vs. occurrence, similar names, an unnamed meaningful group, two coordinated buildings, and a broad attacker plural. It should assert the compiled per-pass prompts preserve these distinctions and retain the existing evidence requirements; it must not assert a model's answer or merely check that an isolated prompt string exists.

No provider/model execution, fresh Session 29 rerun, candidate comparison, publication, database/service operation, runtime restart, or 5202 change is authorized in this slice. After independent review, PRIME will direct the next real comparison. If fixing any failure requires runner/consolidator behavior, a schema, or a path outside this lease, stop and send PRIME the exact contract and paths before editing.

## Activation evidence

PRIME confirmed the exact base, existing checkout, single-PR topology, path allowlist, exclusions, and test boundary. The branch is created from the current GitHub `main` SHA above. The first branch commit is this handoff, before profile or test edits.

## Implementation evidence — 2026-10-17

The recap profile now compiles the source-faithfulness rules into its actor, location, collective, beat, encounter-job, and edge pass instructions. The shared evidence rule and Worldbuilding profile are unchanged. The synthetic fixture reaches the real `render_category_pass_prompts` boundary and checks the five source distinctions at their owning pass, the existing quote/evidence fields, and that recap-specific guidance does not leak into the Worldbuilding profile.

Verification passed:

- `python -m pytest -q tests/test_recap_source_faithfulness_profile.py tests/test_extraction_profiles.py tests/test_category_candidate_graph_extractor.py`: 14 passed.
- `git diff --check`: passed for the modified profile; the new handoff and test were checked for trailing whitespace and final newlines.
- GitHub's cumulative comparison confirms the branch is based on `main@541a8201405eb231f136a19963dc89b22d92f1b0`, 0 commits behind, with only the three leased paths. Remote file contents match the local tested files byte-for-byte. All `src` and relevant extraction test files in the local checkout are unchanged from that base.

The local linked Git metadata is mounted read-only, so GitHub's branch/content APIs were used to create and update this isolated PR branch. No unrelated dirty files were moved or overwritten. The tests verify prompt construction only; no model/provider run, real-candidate comparison, publication, or rendered Ingest acceptance was performed.
