# HANDOFF — SBW11 Committed Plan-document content hydration and reload

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — not blocked on `SBW10`; dispatch once current workspace-document and two-phase Markdown writer contracts are re-anchored. Required before `SBW12`.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw11-plan-document-content-hydration.md`  
**Workstream:** `SBW11`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability: a registered Plan document can read and hydrate its committed Markdown content after a fresh browser/session reload. Do not add the statblock embed node, change write semantics, create generic file browsing, or migrate every workspace document type.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Read committed content for one registered workspace document | Yes | Yes API/read contract | Yes | Include |
| Hydrate Plan Tiptap state from that content | No; required user proof | No | Yes | Include under same invariant |
| Preserve unsaved local work precedence safely | No; required state contract | Existing local persistence | Yes | Include |
| Add statblock Markdown/Tiptap node | Yes | Yes | Yes | Successor `SBW12` |
| Rewrite two-phase save | Yes | Yes | Yes | Exclude |
| Generic arbitrary repo file reader | Yes | Yes | Broad | Exclude |

**Selected capability:** opening a registered Plan document in a fresh state loads its committed Markdown rather than silently constructing starter content.

**Why included rows share one invariant:** backend read and frontend hydration are one observable save/reload contract; local-draft precedence must be defined to avoid overwriting unsaved work.

## §1 Mission

A GM can reopen a committed Plan document and recover its saved Markdown content in the Tiptap canvas so later typed embeds and authored blocks survive real reload rather than only localStorage continuity.

**Invariant**

```text
For an exact registered document revision, committed content is read only from its allowlisted target and hydrated deterministically; a newer unsaved local draft is never overwritten silently, and missing committed content never masquerades as saved data.
```

**Mission falsification test**

```text
This is not one slice if implementation must also add statblock directive parsing, change commit/write behavior, browse arbitrary paths, reconcile multiple editors, or migrate runbook/build surfaces.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Plan Surface Toolbox; workspace-document registry; two-phase Tiptap Markdown writer; integration roadmap dependency for `SBW12` |
| Repository rules | `AGENTS.md`; corpus path allowlist and two-phase writer safety; external-agent PR loop |
| Base revision | Current merged main SHA at dispatch |
| Predecessor contract | `WorkspaceDocumentRecord` metadata/revision/target relpath, committed Markdown target, `markdownToTiptapDoc`, local Tiptap state schema |
| Exact input consumed | Exact workspace `document_id` and registry record; server-owned target relpath resolution |
| Named successor | `SBW12` revision-pinned statblock embed |
| What remains false | No new block type exists; no write/commit behavior changes |
| Explicit non-goals | Statblock node, arbitrary path query, generic repository editor, conflict merge UI, runbook migration, graph read/write |

Read in order:

1. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
2. current workspace-document registry/routes/tests
3. current Tiptap Markdown prepare/commit writer and tests
4. `PlanSurfaceCanvas.tsx`, `planSessionDescriptor.ts`, `tiptapLocalState`, `markdownToTiptap.ts`, `usePlanMarkdownSave.ts`
5. current Plan route initialization/loading tests

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Fresh open existing committed document | Registry metadata loads, canvas may use starter content | Read exact committed target and hydrate parsed Tiptap doc | Yes | route/service + Plan loader |
| Existing local unsaved state | localStorage used | Preserve when it belongs to same document and is newer/dirty under explicit policy | Yes | local state/loader |
| Clean local cache older than committed revision | May still win by existence | Replace with committed content | Yes | loader |
| New document with no committed file | Starter content | Explicit uncommitted/empty starter state | Yes | loader |
| Target file missing unexpectedly | Could appear as starter | Typed missing-content diagnostic; do not label committed | Yes | route/loader |
| Target outside allowlist/path traversal | Server registry should prevent | Reject; no arbitrary read | Yes | service/security |
| Invalid/unsupported Markdown | Parser returns diagnostics | Hydrate supported content and surface diagnostics without changing source | Yes | parser/Plan loader |
| Stale registry/file revision | Current metadata revision may not fingerprint content | Read response binds registry revision and content fingerprint/metadata | Yes | read service |
| Save then reload fresh browser | Not reliably proven | Saved content returns equivalently through parse/serialize contract | Yes | end-to-end |
| Dependency unavailable/read error | Generic Plan load failure | Honest error with retry; do not overwrite local dirty state | Yes | loader/UI |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify/Create | `apps/live_control_server/services/workspace_document_registry.py` or bounded content-read sibling | Resolve exact registered target and return safe content view |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | Add exact document-content read endpoint or expand exact read response intentionally |
| Create/Modify | focused workspace document content-read tests | allowlist/missing/fingerprint/round-trip proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | content-read response type |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | exact content read call |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | mapping/error proof |
| Modify | `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts` | load committed content as initialization input |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | initialize from resolved content/local precedence rather than unconditional starter |
| Modify | `apps/live-control-ui/src/tiptap/state/tiptapLocalState.ts` | explicit document revision/fingerprint/dirty precedence fields if needed |
| Modify | `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts` | only diagnostic/round-trip support required by existing Markdown, not statblock directives |
| Create/Modify | focused Plan initialization/local-state/parser tests | owning-boundary proof |

### Bounded discovery exception

```text
Directory: apps/live_control_server/services/, apps/live-control-ui/src/planSurface/, apps/live-control-ui/src/tiptap/
Maximum additional paths: 6
Allowed path kinds: existing writer target allowlist helper, Plan route loader/hook, local-state schema/test, parser fixture/test
Decision rule: include only to establish exact committed-content hydration and local-draft precedence
Required report: identify current content-status/revision vocabulary and every additional path
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| statblock directive/parser/node/resolver | `SBW12` |
| changes to `prepareTiptapMarkdownWrite`/commit tokens | save path already owns writes |
| arbitrary repo/corpus file read endpoint | security and scope violation |
| generic merge/conflict editor | separate capability |
| automatic recovery of corrupt Markdown | preserve source and report diagnostics |
| runbook/build/play document hydration breadth | dispatch only Plan unless same existing contract already covers them without added outcome |
| graph resolution | unrelated |
| full Markdown parser redesign | only existing supported semantic subset |

## §6 Implementation contract

### Content-read response

```text
WorkspaceDocumentContentV1:
  schema
  document_id
  registry_revision
  title/campaign/kind/status/content_status
  target_relpath               # repo-relative display-safe
  content_found
  markdown?                    # bounded response
  content_sha256/fingerprint?
  modified_at?                 # if safely available
  diagnostics[]
```

Rules:

- Server accepts only `document_id`, never a caller-supplied path.
- Resolve record through registry and existing safe target-relpath policy.
- Read only the registered target under approved repository/corpus roots.
- Bound file size and response body.
- Do not expose absolute path.
- Missing file for a draft/uncommitted record is an ordinary no-content state; missing file for a record marked committed is a diagnostic/integrity state.
- Read is side-effect-free.

### Frontend initialization precedence

```text
1. exact dirty local state for same document, when local base registry revision/fingerprint is compatible
2. otherwise exact committed content from server
3. otherwise starter content only for a genuinely uncommitted/no-content document
4. otherwise explicit error/unresolved state
```

The implementation must define compatibility precisely. Recommended v1:

- local state stores `base_registry_revision`, optional `base_content_fingerprint`, `dirty`, and timestamps;
- dirty local state based on the same current registry revision wins, with a visible unsaved-state label;
- dirty local state based on an older committed revision is a conflict/recovery state, not silently loaded or overwritten;
- clean local state is cache only and never wins over a newer committed response;
- local state for another document never participates.

```text
Input:
  exact document_id/registry record + optional local state

Output:
  deterministic initial Tiptap JSON, source classification, diagnostics, and save base revision

Invariant:
  committed content and unsaved local work are never confused or silently overwritten

Failure behavior:
  missing registry record -> 404
  unsafe target -> reject
  missing committed file -> integrity diagnostic/error
  read unavailable -> preserve compatible dirty local state if present; otherwise error/retry
  parser diagnostics -> hydrate supported content, preserve raw committed Markdown on server, surface diagnostics
  stale dirty local base -> conflict/recovery UI; do not auto-merge

Replay / idempotency:
  same document revision/content/local state -> same initial Tiptap doc/source classification
  repeated read -> side-effect-free
  save then fresh read -> committed content/fingerprint changes according to existing writer

Trust boundary:
  Verifies: document ID, registry target, safe path, size, local state document/base revision, content fingerprint
  Records without proving: semantic correctness of Markdown content
  Rejects: arbitrary path, absolute path, cross-document local state, silent stale-local merge
```

### §6A State and fallback matrix

| Path | Loading | Success | Ordinary miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Content read | exact record/target | bounded Markdown + fingerprint | uncommitted no file | typed unavailable | committed file missing/unsafe/corrupt read fails | registry changed → reread | safe |
| Plan init no local dirty | wait for server | committed parse | starter only if truly uncommitted | error/retry | diagnostic/error | reread current | safe |
| Plan init compatible dirty local | load local with unsaved label | local wins | N/A | local may remain usable | local schema invalid → do not trust | old base conflict | explicit discard/recover later, no auto-merge |
| Clean local cache | defer to server | server wins | starter if uncommitted | error rather than stale cache unless policy explicitly permits named fallback | cache ignored | ignored | safe |

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Document | exact registry `document_id` | none | No title/path lookup | all content/local state keyed by ID |
| Target | registry-owned validated relpath | mismatch/unsafe fails | No caller path | server read only |
| Registry revision | exact positive version | changed = stale local/base | No | save base |
| Content | optional fingerprint over exact bytes | mismatch = changed content | No | cache/dirty compatibility |
| Local state | exact document ID + base revision/fingerprint | mismatch conflict/ignore | No cross-doc | unsaved recovery |
| Rename/target metadata update | document ID stable; revision increments | none | No | content reread against current target |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Existing Markdown save | current two-phase writer target | save then read returns exact committed bytes before parsing | existing commit semantics | unchanged | existing backup/commit behavior |
| Content read | none; derived response | exact bytes/fingerprint | safe repeat | response schema versioned | N/A |
| Local state write | versioned localStorage record | dirty Tiptap JSON + base revision retained | replace same document state | migrate/ignore unknown schema explicitly | user can clear local state |
| Hydration | derived | parse/serialize semantic round-trip within supported subset | deterministic | diagnostics for unsupported content | source unchanged |

### §6D Predecessor-to-consumer mapping

**Grounding source:** current `WorkspaceDocumentRecord`, writer commit response, local Tiptap state, `markdownToTiptapDoc`.

| Predecessor field/outcome | Consumer behavior | Rule | Proof |
|---|---|---|---|
| document ID/revision/status/content status/target relpath | content read/init | exact copy and policy | route/loader tests |
| committed Markdown bytes | parser input | no pre-normalization beyond newline policy explicitly tested | round-trip fixture |
| local document ID/dirty/timestamps | precedence | exact same doc only | local tests |
| new base revision/fingerprint fields | conflict/cache policy | strict | migration tests |
| parser diagnostics | Plan load warnings | preserve messages/line | parser/Plan tests |
| missing target | ordinary vs integrity based on record status | no starter masquerade | route tests |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Only registered safe target read | service/route | traversal/arbitrary path tests | rejected/no absolute path |
| Save→fresh reload restores content | writer/read/Plan integration | end-to-end test | semantic Tiptap content equal |
| Compatible dirty local wins visibly | Plan loader/local state | component/unit test | unsaved source classification |
| Stale dirty local not overwritten | loader | conflict test | no auto-load/overwrite |
| Clean cache cannot hide newer commit | loader | revision/fingerprint test | server content used |
| Missing committed file honest | route/Plan | fixture | integrity state, no starter |
| Unsupported Markdown diagnostic | parser/Plan | fixture | content preserved, warning shown |

Required commands:

```bash
uv run pytest <workspace document content-read and writer tests> -q
cd apps/live-control-ui && npm test -- --run <Plan initialization/local-state/parser tests> src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Create/open a Plan document, edit and commit Markdown, clear the document's localStorage entry or use a fresh browser profile, reopen by document ID, and show committed content. Then create a dirty local edit, reload, and show it is retained with an unsaved label. Change the committed revision externally and show stale local conflict rather than silent overwrite.

## §8 Required handback

Include exact content-read response, local precedence table, base/head, paths, commands/results/provenance, save→fresh-reload evidence, stale/local/missing diagnostics, baseline failures/waivers, and confirmation that no statblock node/write redesign/generic file reader ships.

## §9 Acceptance rubric

- [ ] Server reads content only by exact registered document ID and safe target.
- [ ] Fresh open hydrates committed Markdown, not starter content.
- [ ] Truly uncommitted no-content documents alone receive starter content.
- [ ] Dirty local state precedence is exact, visible, and revision-aware.
- [ ] Stale local state is not silently merged or overwritten.
- [ ] Missing committed file and parser diagnostics are honest.
- [ ] Existing two-phase writer semantics remain unchanged.
- [ ] No statblock embed or generic arbitrary file reader ships.

## §10 Reviewer protocol

Start with the save→fresh-browser reload path. Audit path safety, content size, revision/fingerprint semantics, dirty-local precedence, missing committed file, and parser diagnostics. Search for caller-supplied paths, starter fallback after errors, and localStorage unconditional wins.

## §11 Re-review protocol

Rerun fresh reload, compatible dirty, stale dirty, clean cache, missing committed target, unsafe path, and unsupported Markdown tests after every fix.

## Stop conditions

Stop if:

- the registry cannot safely resolve/read committed targets without a broader storage contract;
- writer revision does not provide enough information to define local compatibility and adding a content fingerprint becomes a separate durable contract requiring tracker approval;
- Plan initialization architecture cannot defer content until read without a separate loading-shell refactor;
- existing Markdown cannot round-trip through the supported parser sufficiently for committed documents;
- a generic file endpoint or writer change becomes necessary;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor current registry/writer/local-state schemas.
- [ ] Resolve exact dirty-local compatibility rule.
- [ ] Capture save→fresh-reload fixture.
- [ ] Confirm `SBW12` statblock embed remains false.
