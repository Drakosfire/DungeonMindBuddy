---
title: Saved World Plan as a Playable Run source
document_class: design
status: proposed_for_review
version: 0.1
created_at: "2026-10-04"
workstream: DEMO
design_base: "Buddy main 0f42fec0812655bb37c87b6be9a7fe5741d7f25f"
companion_handoff: "../Plans/HANDOFF-world-plan-playable-adoption.md"
---

# Saved World Plan → Playable Run

## Decision

A saved World Plan may be selected as the source of a new Run without changing
what the Plan is. Starting Play binds the Run to the same World-owned WorkObject
and one exact committed WorkRevision. It does not convert the Plan to a Runbook,
copy its Markdown, or create a second content identity.

The identity tuple is:

| Part | Authority |
| --- | --- |
| World | The selected, verified World ID |
| Authored document | The existing World-owned Plan WorkObject ID |
| Exact authored version | WorkRevision ID, revision number, and content SHA-256 |
| Mutable play state | The new Run ID and its independent Run revision |

The existing Run field named **playable_artifact_id** is a legacy wire name for
the stable WorkObject ID. For a Plan-backed Run it continues to carry the Plan's
ID; it must not imply a second Playable artifact or a kind conversion. The
Run's World and exact WorkRevision pin remain explicit and authoritative.

WorkObject kind is part of source identity: it remains **plan** before and after
Start Play. APP-STATE owner confirmation at Buddy main
6feb3059b2da4d2ec29966ce9723f0effc70108f is that supported Content APIs keep
kind stable: mutation guards check the locked kind, update SQL does not write
kind, and imports assign it at creation. The design relies on this supported
application-mutation invariant and its owning regression tests, not on a
database trigger. Privileged direct SQL can bypass application contracts; that
out-of-contract possibility alone does not block Plan-to-Play or justify a
migration. No separate source-kind field is needed in the Run or manifest now.
If a future supported writer can retag kind, stop and review the smallest
versioned source-kind receipt with APP-STATE before admitting it.

The confirming evidence is the kind check in
**src/application_state/content/service.py**, the metadata update in
**src/application_state/content/repository.py** which does not write kind, and
the fixed-kind import/conflict behavior in
**src/application_state/content/import_plans.py** and
**src/application_state/content/import_runbooks.py**. The owning regression in
**tests/application_state/test_runbook_work_object_postgres.py** proves that
supported Plan/Runbook mutation APIs reject cross-kind operations.

## Why this is the minimum coherent model

Buddy already stores World Plans and Runbooks on the versioned Content
substrate, and the current Play Run record already pins a WorkObject, exact
WorkRevision ID, revision number, and digest. Reusing the Plan's identity keeps
editing, history, and Play pointed at one authored authority.

The current admission boundary is narrower than that product model: the shared
committed-revision helper can read a World Plan, but the Start Run preflight,
Content Playable admission, and pinned-Run resolution currently require a
Runbook. This is a real cross-boundary contract gap, not a reason to disguise a
Plan as a Runbook. The implementation must widen the explicitly typed
World-Plan-to-Run path at each owning boundary and prove it end to end.

Alternatives rejected:

- Copy Plan Markdown into a newly created Runbook: creates two editable
  authorities and makes identity, update, and provenance ambiguous.
- Retag or mutate the Plan's kind: destroys the distinction between
  preparation and Runbook authorship.
- Bind a Run to “whatever is current” or a browser-local draft: lets a later
  edit silently change the material an existing Run means.
- Generate Playable structure from headings or prose at Start time: invents
  durable identities and semantics that the GM did not author.

## Start eligibility and transaction

Start Play is an explicit GM action against the selected World Plan. Before a
new Run exists, the owning service must atomically establish all of the
following:

1. The requested document exists and is a World-owned Plan, with no Campaign
   owner, under the currently selected World.
2. The Plan is active and has an exact current committed WorkRevision.
3. The selected revision is that current revision; the WorkRevision ID,
   revision number, and digest agree.
4. There is no divergent working copy. A dirty draft is not a startable saved
   basis, even if an older committed revision exists.
5. The exact committed Markdown passes the existing server-owned Playable
   structure and manifest admission. All element IDs, containment, and authored
   edges are valid, and the document satisfies the existing Run-readiness rule
   for its admitted grammar. Do not silently narrow support to v2: the current
   manifest parser also supports the v1 Scene-first grammar. In particular,
   the v2 nonzero-Beat check is not a new v2-only filter for otherwise valid v1
   content.
6. The Run and sealed reference manifest are created atomically from that same
   WorkRevision, preserving the World, WorkObject ID, WorkRevision ID, revision
   number, and digest.

The check belongs in the application-state transaction, not only in a UI
preflight. A stale revision, wrong World, non-Plan source, divergent draft,
unsupported/malformed structure, or manifest failure creates no partial Run
and no second content object. A retry for the same Run ID and same complete
binding may return the existing exact Run; the same Run ID with any different
World or source binding conflicts. A same-binding replay is historical
idempotency: if that Run already exists, return its stored Run and manifest
without rechecking whether the Plan is still current or clean and without
rewriting the receipt. Current-and-clean admission applies only when creating a
new Run ID.

The first implementation should reuse the existing WorkObject, WorkRevision,
Run, and manifest authorities. It must not add a copy table or new content
store. Any proposed schema or public request expansion requires a concrete
missing-capability argument and a separate review before activation.

## Structure and projection

The existing server-side Playable marker/manifest derivation is the sole source
of Run structure. It recognizes the repository's existing v1 Scene-first and
v2 Beat-first forms and rejects invalid identity, containment, duplicate IDs,
malformed edges, mixed/unsupported grammar, and other states already rejected
for Playable admission. Preserve each form's current readiness behavior; do
not translate v1 into v2 or reject valid v1 content solely for not using
Beat-first organization. Ordinary Plan headings and unmarked prose do not
become Beats, Scenes, Choices, or Options by inference. No new grammar or
automatic marker insertion is introduced here.

The manifest is an index of stable semantic element IDs, not a content copy.
Play must continue to resolve the Run's exact pinned WorkRevision for its
authored text; later Plan revisions may not be substituted. The complete
committed Markdown remains GM-inspectable even where a first Play projection
uses marked elements for navigation.

The first projection is GM-only. Existing Plan/Playable markers do not encode
reviewed player-audience visibility. Missing or unknown audience metadata must
not be treated as public or player-safe. Player projection needs a later,
explicit audience-classification contract and review.

## Revision and Run-state behavior

- Start requires the latest committed Plan revision and a clean working-copy
  boundary. No draft bytes or stale “last known good” revision are substituted.
- Existing Run replay and read are a separate path from new-Run admission.
  Replay returns the original Run/manifest binding without current/clean
  re-admission. Opening an existing Run resolves its exact retained
  WorkRevision ID, revision number, and digest; it does not require the Plan to
  remain active or current. Wrong World or mismatched immutable identity still
  fails closed.
- Once created, a Run remains pinned to its exact historical Plan WorkRevision,
  even if the Plan is edited, saved, renamed, or later discarded. The exact
  pinned content remains readable or the Run fails closed; it never falls
  forward to the Plan's new current revision.
- A normal Plan Save creates a new WorkRevision. It does not rewrite an
  existing Run. A later Start Play action may create a different Run bound to
  the new current revision.
- This slice does not add automatic or implicit rebase. The current Run rebase
  contract is Runbook-specific; Plan-backed rebase requires separate admission
  review and must be an explicit user action if it is later authorized.
- The Plan continues to own authored prose and GM Note blocks. A Run owns
  selected Options, resolved/runtime state, and its Run-local notes. Runtime
  notes never overwrite authored Plan notes. Additional durable roll/outcome
  types are outside this source-adoption contract and need their own owning
  state design.

## Authority and security boundaries

Starting or playing from a Plan is not Graph publication. A dmb-ref or other
source/Graph pointer remains navigation/provenance text; it does not authorize
a Graph read, establish evidence, or publish a World claim. No Plan save,
Start Play, choice, note, or Run outcome implicitly writes DungeonMind Graph
canon.

Buddy remains the authoring and Run projection boundary. DungeonMind remains
World identity, Graph knowledge, and governed evidence authority. This design
does not call a model/provider, move credentials, copy private corpora, or
change the separate GenerationEngine parity workstream.

## Review and next gate

This document proposes the contract for PRIME review. It does not amend the
active product roadmap or authorize implementation. The companion handoff is
BLOCKED. It requires re-anchoring, review of the product sequencing
prerequisites, APP-STATE confirmation of WorkObject-kind immutability, and an
explicit path/owner/runtime-resource lease before any executable work.
