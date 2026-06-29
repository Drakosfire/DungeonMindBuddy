# Graph Memory Static Preview Graph UI Prototype v0

## Purpose

This PR creates a static prototype artifact. It does not implement production frontend UI. The artifact makes the Preview Graph UX tangible for design review by rendering Session 23 candidate graph inspection panels into one checked-in HTML file.

## Why This Comes After Preview Graph UX Design Spec

The prior rung defined the GM-facing preview experience in prose, wireframes, and component contracts. This rung converts that design target into a deterministic review artifact before any app/runtime integration exists.

## Static Prototype Boundary

The prototype is rendered from checked-in fixture/report data only. The prototype does not approve, reject, defer, persist, or write graph memory. The prototype is a review artifact, not campaign truth and not a durable memory surface.

No live model execution, live extraction, graph writes, approval persistence, graph queries, corpus scanning, corpus mutation, `/plan` integration, Agent Interaction integration, fact promotion, canon promotion, production frontend routing, or runtime behavior changes are introduced by this PR.

## Source Inputs

The prototype model is built from the static extractor output comparison report and the eval-only extractor harness candidate bundle for Session 23.

## Prototype Model

`evals/graph_memory_layer/examples/static_preview_graph_ui_prototype/session_23_preview_graph_ui_prototype_model.json` is the view-model consumed by the static renderer. It is builder-locked and must exactly match `build_prototype_model()`.

## Rendered HTML

`evals/graph_memory_layer/examples/static_preview_graph_ui_prototype/session_23_preview_graph_ui_prototype.html` is a single standalone HTML document. It has no external scripts, stylesheets, images, iframes, network calls, React imports, forms, or storage behavior.

## Preview Summary Section

The summary shows Session 23 status, GM preview readiness, safety/evidence/high-risk pass state, merge gate, hard failures, soft misses, and the recommendation to inspect without bulk approval.

## Coverage Section

The coverage cards show nodes, edges, beats, proposed writes, ignored items, and deferred items as candidate/gold counts with clear bands.

## Evidence Health Section

The evidence panel shows total, resolved, openable, highlightable, warning, unknown-anchor, heading-only, and source-leakage values.

## High-Risk Audit Section

The audit panel lists high-risk audited objects and forbidden claims absent, while stating that audited claims still require careful review.

## Candidate Explorer Section

The explorer renders static groups for nodes, edges, beats, ignored items, and deferred items with labels, IDs, types, evidence counts, risk/warning state, proposed-write state, and disabled review state.

## Candidate Detail Examples

The detail examples focus on Lysandro, the Lysandra-recognizes-Lysandro edge, and the remaining approaching horde thread. They show evidence labels and short metadata rather than raw recap text.

## Proposed Writes Queue

The proposed writes queue shows all sample proposed writes as pending with evidence counts and visible disabled reasons.

## Missing Coverage Panel

The missing coverage panel groups missing gold coverage by type and explains why this safe sample is still not ready for GM preview.

## Hard Failures Panel

The hard failures panel shows the current no-hard-failures empty state and explains how hard failures would keep approval-like controls disabled.

## Disabled Review Controls

Disabled approve, reject, defer, needs-more-evidence, and campaign-context-required controls are visible with reasons that are not tooltip-only.

## Accessibility and Legibility

The prototype uses a main landmark, section headings, table captions, disabled button elements, visible labels, high-contrast default styling, and text labels rather than color-only status.

## Determinism Requirements

The checked-in model must exactly equal the builder output. The checked-in HTML must exactly equal the renderer output for that model. Validators reject runtime/app/network leakage.

## Why This Is Not Runtime UI

The prototype is static HTML under eval fixtures. It does not add React components, routes, API endpoints, app state, production retrieval changes, or runtime behavior.

## Future Frontend Implementation Gate

Future frontend work can use this artifact as a target, but must still pass separate gates for runtime safety, approval persistence, graph writes, query behavior, and GM review controls.

## What This Does Not Do

It does not call an LLM, execute extraction, generate output from recap text, write graph memory, approve writes, persist review state, execute graph queries, scan or mutate corpus files, connect `/plan`, connect Agent Interaction, promote facts, promote canon, or change runtime behavior.

## Deferred Work

Deferred work includes query vocabulary fixtures, future runtime UI design gates, explicit approval persistence design, graph write safety gates, and production integration planning.
