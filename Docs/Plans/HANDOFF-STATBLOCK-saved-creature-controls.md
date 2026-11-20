# STATBLOCK: saved World creature controls

SETTLED: merged/delivered; native creation is owned by the bounded successor
HANDOFF-STATBLOCK-native-threat-creation.md.
Serial successor to merged2240 (733eb54c7ee3a030ce67804ee9e01c362f20cd7e).
Branch codex/saved-world-creature-controls from remote main64cb0b5c89f685505c7558207e4943e6cf76cac4;
reuse buddy-context-loop, no new checkout/environment. ADVERSARY2242 owns native
execution and its retrieval handoff; this UI-only slice has no overlapping paths.
LocalWorld lanes do not own this workbench. Existing Play retrieval holds remain.

Outcome: reopening verified saved World mechanics exposes the existing native
creature-association controls without reopening an expired generation candidate.
The current saved-draft restore deliberately skips that candidate, but association
is incorrectly nested under its view. Move the existing panel to the verified
saved-draft boundary alongside the shared editor entry. Mount it only after a
fresh correct-World draft snapshot and hide it during pending/unavailable reads.
Do not change the association request, selected version, native reader, authority,
Save/recovery, publication, image workflow or creation behavior.

Expected writes: this handoff; predecessor
Docs/Plans/HANDOFF-STATBLOCK-native-creature-mechanics.md (truthful settlement);
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx;
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx.
No backend, schema, config, App, provider or retained data writes. Runtime delivery
uses the existing guarded UI-only owner after review/CI; no live changes while
implementing. Stop/split any new capability or contract.

Verification: owning workbench tests must prove saved-draft restore with an expired
candidate exposes the association panel without reading/generating a candidate;
foreign, pending and failed draft reads must not expose it. Existing native panel
checks cover selection/replay and its request guards. Run affected tests and build,
inspect cumulative diff, independent review, push/open PR, merge and protected
UI delivery. Repeat the captured read-only ordinary-controls check; retain its
initial timeout evidence. No dogfood or operator acceptance claim.

Validation: the saved/expired-candidate owner test failed before the host move
(the missing association region matches the retained browser timeout). After the
move,164 workbench/panel cases and TypeScript/production build pass. Initial
verification-command path typo is retained separately and is not the regression
witness. No production request/authority behavior changed; review/CI/delivery
remain pending for this successor.

Settlement: sourcef0516d6 merged e420387cd; UIad53fdabbe99 is live on5202.
Independent source/integration/frozen-artifact/transport approval,164 tests/build,
all7CI, preflight and served ordinary-controls verification passed. Creature
selection after saved-draft restore now shows158 exact scope choices/132 actors
without loading the temporary candidate. One editor, unsaved text and portrait
instructions survive Toolbox/full-reader/Back. No provider/content writes; retained
rows/session/schema133 conserved. Original host timeout/red test retained. Native
Graph threat creation, exact successor association and shared previews remain open.
