# INGEST: apply common recap faithfulness to every claim-bearing pass

Status: COMPLETE; implementation lease released. PRIME
confirmed disjoint profile/test ownership and authorized activation after PR2045
merge. PR2045 merged as `e7c0ec84508d212c7dc211c7c270393534e7b375`.
Base: `e7c0ec84508d212c7dc211c7c270393534e7b375`.
Branch: `codex/recap-common-faithfulness`.
Checkout: `/home/drakosfire/Projects/.codex/249d/DungeonMindBuddy`.

Outcome: every ordinary recap claim-bearing extraction pass receives the same
common modality, attribution, time, scope and identity guidance. Pass-specific
instructions remain additional guidance rather than a condition for common rules.
Worldbuilding prompts and source/evidence representation remain unchanged.

Observed boundary: at head 793b8955df5608f5686e47fc21b5c8fa609a144f,
render_category_pass_prompts omits the common recap block only from object_pass.md
and thread_pass.md. The wrapper's early return for absent pass-specific mapping
owns this omission. The retained S5 thread-handle failure remains separate:
undeclared shortened handles must still be rejected, never guessed or repaired.
Missing common guidance is not proof of causation for those handle failures.

Topology: serial successor to merged PR2045, not a stack. PRIME’s retry repair
PR2046 and shared diagnostics investigation are disjoint. No live runtime,
provider, database or publication lease is included.

Exclusive expected write set:

- src/graph_memory/extraction/recap_extraction_profile.py
- tests/test_recap_source_faithfulness_profile.py
- Docs/Plans/HANDOFF-INGEST-recap-guidance-coverage.md
- Docs/Plans/HANDOFF-INGEST-recap-directed-edge-faithfulness.md, truthful
  predecessor merge settlement only.

Implementation boundary: remove the accidental coupling between common guidance
and optional per-pass guidance at the existing profile wrapper. Do not invent a
second rule block, alter canonical evidence handles, change profile identity,
add fallback producers, introduce schema fields or change Worldbuilding rules.
Critique: applying recap guidance to all passes must not accidentally transform
non-recap profiles or duplicate common guidance on mapped passes.

Validation: reproduce missing instructions through ordinary prompt construction;
assert each real recap pass receives one common block and retains its own task,
evidence contract and optional specific instructions. Confirm Worldbuilding
prompts do not receive recap-only instructions. Run owning profile/prompt checks.
This verifies prompt delivery only. Later qualified isolated actual model captures
must separately measure object/thread recall, unsupported assertions, source
attribution, valid evidence handles, host conservation and publication fidelity.
Do not claim model improvement from string tests or repair bad handles by suffix.

Completion: inspect cumulative diff, commit, push and open one PR for PRIME review.
Merge/runtime delivery remain separate. No provider, runtime, database, publication
or primary-data effects are part of this code slice.

## Implementation evidence

The owning ordinary prompt regression reproduced one failure with four passing
controls before the fix. The wrapper now treats pass-specific guidance as
optional while always applying the existing common block. No new per-pass
semantic rules or source-handle repairs were added. All 44 focused profile,
category-extractor and source-quote checks pass; Ruff and diff checks pass.

Exact-base prompt replay changes only object_pass.md and thread_pass.md. Existing
mapped-pass prompts are byte-identical, all ordinary recap prompts have one common
block, and other profile metadata, shared renderer/catalog and Worldbuilding
owner files remain unchanged. Actual model and publication effects are unmeasured.

## Settled predecessor

PR2047 merged as bbf71bc2293fa31a4b1931fa39d0352721aa4308 after independent
approval and all seven original-head CI checks. Its common-guidance code was
conserved-delivered with PR2048 at ba208e8002413f3aec228d3ac7ec7fe715fe40dc.
Proof: q01-published-graph-authority/recap-common-and-party-retirement-api-delivery-proof.json
under the existing private runtime-evidence owner: MERGED_DELIVERED,8956source
blobs verified, all91primary tables/nine session files/savedPlan/UI conserved,
zero providers/database writes/dependency changes. PR2049 subsequently delivered
that predecessor unchanged at1e5ae2d0. Actual S6 capture now exercises the ordinary
pipeline, but its mixed qualification failures do not imply this routing fix
failed: common guidance reached the passes and the model still overasserted.
The bounded prose-qualification successor owns further instruction changes;
this handoff grants no remaining exclusive write lease or quality acceptance.
