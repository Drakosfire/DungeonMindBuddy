# REPORT — PR #697 complete World-object live §13 witnesses

**Recorded:** 2026-09-09  
**Buddy PR:** #697  
**Implementation head (nano-commit A):** `73ebf4976264b2a5bd1941419eee6868fc807c6a`  
**Canonical handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v2.md`  
**Mode:** in-process product read (`project_complete_world_object` / selected-object Agent envelope) against this checkout. No World or APP-STATE writes.

DSN passwords, `.env` contents, and source prose are omitted.

---

## Authority coordinates (sanitized)

| Field | Value |
| --- | --- |
| Repo HEAD at witness | `73ebf4976264b2a5bd1941419eee6868fc807c6a` |
| DungeonMind World | `dungeonmind_cutover_live` @ `127.0.0.1:54330` (read-only) |
| Buddy APP-STATE | `dungeonbuddy_application_state` @ `127.0.0.1:54331` (read-only) |
| Disposable tests | tmpfs PostgreSQL `dungeonbuddy-disposable-54329` @ `127.0.0.1:54329` |
| World head before/after | `rev:680c246047d67f9fe0293ee90526f670` unchanged |

No `down -v`. Durable named volumes were not touched.

---

## APP-STATE batch test

Disposable 54329 was started as test infrastructure only (`postgres:16`, tmpfs data dir, user `dungeonmind`). Live `54330` / `54331` containers stayed up.

```text
uv run pytest tests/test_world_graph_object_projection.py::test_source_markdown_batch_is_one_query_for_multiple_bindings
.  1 passed
```

---

## A–E — Karsemine / C2S25

Selected node `pc:karsemine` (label Karsemine) with campaign `longmont-c2` and session focus `session-25`. Completeness `complete`, `truncated_fields=[]`. Snapshot `scope_mode=world` (World-cross-campaign truth) while focus remained S25.

| Surface | `originSurface` | fingerprint | revision | rels in/out | assertions | bindings | excerpt_ready | total_ms | world_read_ms | batch_ms |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ingest | ingest | `790f70ea…9636c331` | `rev:680c246047d67f9fe0293ee90526f670` | 15 (6/9) | 1 existence | 31 | 23 | 1063.1 | 960.3 | 99.7 |
| Plan | plan | same | same | 15 | 1 | 31 | 23 | 985.1 | 933.4 | 49.7 |
| Build | build | same | same | 15 | 1 | 31 | 23 | 920.6 | 875.0 | 43.5 |
| Play | play | same | same | 15 | 1 | 31 | 23 | 1009.4 | 958.7 | 48.2 |
| Agent selected-object | agent | same | same | 15 | 1 | — | — | (via same service) | — | — |

Agent selected-object envelope: `status=ready`, `scope_mode=campaign` (lens, not a generic-default change), `completeness=complete`, temporal payload present on relationships, same fingerprint.

Required Karsemine facts:

| Claim | Result |
| --- | --- |
| S25 Lysandra evidence | `edge:node:captain-lysandra-ironveil:allied_with:pc:karsemine` and `…:commands:pc:karsemine`; session-25; 3/3 S25 bindings `excerpt_ready` |
| S24 Hunter's Mark | `edge:pc:karsemine:holds:item-008` → related label Hunter's Mark; session-24; 6/6 S24 bindings `excerpt_ready` |
| S24 Lysandra | `edge:npc_lysandra:commands:pc:karsemine`; session-24 |
| Questionable Company / manual-seed | `edge:pc:karsemine:member_of:party:questionable-company`; evidence `evidence:bundle:v1:manual_seed:pc:karsemine:member_of`; provenance `source_not_durable`; no fabricated excerpt |
| Temporal payload | 16 facts with `temporal_scope.kind=unknown` retained; not dropped, not rewritten to session-25 |
| Honest missing bytes | 6 `source_not_durable` (including party-registry + manual_seed); 2 `span_unresolvable` |

Admitted assertion ledger for this object at this revision is existence-only. That is what authority returned; Buddy did not invent alias/summary/property rows.

---

## Five-consumer fingerprint

```text
Ingest  790f70ea85b8dc5afa3413b52098b813cbbc8cd19bbde07cbabcbb3a9636c331
Plan    same
Build   same
Play    same
Agent   same
revision  rev:680c246047d67f9fe0293ee90526f670
```

Play-local occurrence/Threat chrome is outside this fingerprint by construction.

---

## F — Unrelated ordinary node

`npc_glowkindle` (Glowkindle) under the same C2 + S25 request. Completeness `complete`. 0 relationships, 1 existence assertion, 3/3 bindings `excerpt_ready`, fingerprint `53d51f303781887c…` (different object, as required). Total 521.0 ms.

This is a C1 object served under current-campaign C2 focus, so it also witnesses World-cross-campaign membership. It is not in Karsemine's related-node set.

---

## G — High-degree node

Highest complete neighborhood among probed candidates: `pc:stafl` (Stafl).

| Field | Value |
| --- | --- |
| completeness | `complete`, `truncated_fields=[]` |
| relationships | 24 (22 outgoing, 2 incoming) |
| related nodes | 19 |
| assertions | 1 existence |
| source bindings | 45 (37 excerpt_ready, 6 source_not_durable, 2 span_unresolvable) |
| temporally qualified | 25 (`kind=unknown`) |
| total_ms | 1106.6 |
| world_read_ms | 1055.6 |
| source_batch_read_ms | 47.6 |

24 is the actual admitted degree, not a Buddy cap: `truncated_fields=[]` and completeness is `complete`. Caelynn (21 rels, 1395 ms) and Lysandra (13) were also complete.

---

## N+1 and filesystem

Across the witness process (including not-found candidate probes):

```text
get_complete_object              17
get_source_markdown_batch       10
get_source_markdown               0
```

Every found object used one authority read and one batch join. Zero single-row markdown reads. No filesystem provenance path.

---

## Agent / Build safety (unchanged)

Generic Agent request without `selected_node_id` still defaults `scope_mode="campaign"`. Selected-object context does not change that default; it only adds `selected_node_id`.

Build write admission: `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.test.ts` — 10 passed, including `admitBuildObjectInsert` C1-object-on-C2-document deny and the inverse.

---

## Latency note (not a correctness defect)

Handoff investigation threshold for repeated ordinary-object totals is ~750 ms. Glowkindle (521 ms) is under. Karsemine / Stafl / Caelynn are above; the dominant cost is DungeonMind `world_read_ms` (~875–1056 ms), not APP-STATE batch (~44–100 ms). Recorded as investigation, not accepted baseline, and not treated as a product-join defect.

---

## What remains

- Human STOP after merge (click Ingest/Plan/Build/Play/Agent in the running UI).
- Stage 4 remains NOT DONE.
- Formal implementation review against the evidence commit (nano-commit B).
