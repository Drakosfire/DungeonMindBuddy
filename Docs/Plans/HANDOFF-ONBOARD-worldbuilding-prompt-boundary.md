# ONBOARD — Worldbuilding model-input boundary

Status: ACTIVE. On 2026-11-20 the user explicitly directed this lane to split
the lease with #2087 and fix the prompt leak. Serial implementation from
`origin/main` `f126b6a5a9f76b6b224cabcabbedcb71b2f2592a`; branch
`codex/worldbuilding-prompt-alias`, checkout `Projects/.codex/7550/DungeonMindBuddy`.
No serving ports, operator databases, retained Worlds, paid providers, or
deployment are leased. The predecessor World-creation PR #4240 merged at
`6f8af81e6dd47ec92b5ef9a0180e2e34ffd104c4`; it remains disabled and is not
release-qualified.

## Invariant and failure cases

Worldbuilding model requests must contain meaningful source text and task
instructions but no host source, document, span, World or review-proposal
identifiers, digests, execution bindings, paths, or accounting metadata.
Use request-local aliases resolved by the host to original identities. Keep
the existing source/quote validation and historical evidence authority.
Unknown, malformed, duplicate, guessed, and cross-run handles fail closed.
Do not scrub a rendered prompt by regex or alter user text or quotations.

A fake-provider audit of the Apprentice draft found the source artifact ID
(containing the workspace document ID) in the user prompt on six calls. No
real provider was contacted. The normal node passes construct Source Packet
rows with canonical span/unit IDs. Later inventories can reintroduce those
IDs; advisory edge review additionally serializes source rows, edge evidence,
and constrained edge IDs. The audit had empty candidates, so nonempty later
passes require independent coverage. Full details and the private witness are
outside the repository under the Sizzek evidence directory.

## Explicit ownership split

The user explicitly split ownership with #2087 at head
`687b26a2b83b5fe424801245b1cd199c1d183630`. This lane owns only the
Worldbuilding prompt-alias construction and response resolution regions of
`src/graph_memory/extraction/category_candidate_graph_extractor.py`, plus
`src/graph_memory/extraction/worldbuilding_edge_review.py`, a new host-only
alias helper if needed, focused owning tests (including existing Worldbuilding
profile and edge-review fixtures where their model outputs must use aliases),
this handoff, and the truthful
predecessor status sync. #2087 retains known-character context and its
actor-pass injection; do not edit its feature regions or tests. Open extractor
PRs #2149, #2124, #2118, #1149, and #1148 are independent historical recap
work; preserve their distinct contracts and inspect overlaps before review.
CI inventory may be changed only for new test entries; older CI drafts #2298,
#2299, #2302, #2288 and #3824 do not transfer their unrelated leases.

## Design and verification

Build structured model-safe source packets before rendering; resolve explicit
model-returned alias fields to the original host IDs before existing validators.
Review and nonempty intermediate inventories need structured safe projections;
constrained review IDs and returned choices must use local handles and resolve
to the exact original edges before the existing subset check. Do not weaken
auth, origin, CAS, quote verification, selection or publication boundaries.
Preserve meaningful semantic context and all profile-specific behavior.
Optional vocabulary cautions with an unresolved internal identity must fail
before provider dispatch instead of rendering that identity as a label.

Use synthetic nonempty candidates to capture final serialized provider calls
for every Worldbuilding pass and advisory schema. Prove host identifiers do
not appear while source text and task constraints do; verify exact original
source/span/edge resolution, invalid-handle rejection, unchanged quotes, and
retained candidate evidence. Run owning profile, review, source-fidelity,
provenance and prompt-boundary contracts and exact-head independent review.
After synthetic verification, repeat the private Apprentice fake-provider audit.
No live model call or guest publication is authorized by this slice. Known
frontend full-discovery failures remain red; do not claim release qualification.
