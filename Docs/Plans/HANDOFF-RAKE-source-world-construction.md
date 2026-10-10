# RAKE: resolve source World before strict construction

## Authority and scope

This bounded implementation follows the ACTIVE repair lease in [PR #1068 comment 6097772299](https://github.com/Drakosfire/DungeonMindBuddy/pull/1068#issuecomment-6097772299). It is based on Buddy `main` at `30fcee140772c391d623c61ec2a06c70174d3991`.

The leased paths are:

- `apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py`
- `tests/test_world_graph_source_admission.py`
- `Docs/Plans/HANDOFF-RAKE-source-world-construction.md`

## Repair

Legacy Buddy recap source records can have `world_id=None` or an empty value. The adapter already has an explicit `request.world_id` fallback, but previously applied it after `_store_artifact_v2` constructed strict `SourceArtifactV2`, whose `world_id` must be nonblank. Resolve the World first and pass that value into the constructor.

Preserve a nonblank artifact World as-is, including foreign-scope values so existing ownership/proof gates remain authoritative. Do not mutate the input source object, infer World from campaign, change nullable Core contracts, or alter revision collision mapping, source bytes, or other metadata.

## Verification and boundary

Synthetic tests exercise the actual mapper and strict `SourceArtifactV2` constructor for `None`, empty, and whitespace-only legacy World values, assert the request World fallback, prove the source object is unchanged, and preserve existing nonblank artifact World values. The focused mapper and existing admission/proof checks pass: **11 passed**. Ruff and `git diff --check` pass.

The complete owning test file reports **23 passed, 1 failed**. The failure is the unchanged `test_selected_source_pins_share_one_search_without_opening_content` fixture: its `SimpleNamespace` omits `native.objects`, which the unchanged `world_graph_reads.py` consumer iterates. I ran that exact test on clean base `30fcee140772c391d623c61ec2a06c70174d3991` with the same environment; it fails with the same `AttributeError` at `world_graph_reads.py:2419`. This is inherited and outside the leased adapter behavior.

No provider calls, private corpus, database, prepare, correction service, publication, Core contract, dependency pin, or runtime behavior are part of this repair. A PRIME independent review and a separate authorization are required before any real-data reprepare.

## Implementation handback

This repair is limited to the three leased paths above. The branch head, cumulative diff, focused test evidence, and PR are the implementation handback for independent review. This handoff does not grant merge or real-data execution authority.
