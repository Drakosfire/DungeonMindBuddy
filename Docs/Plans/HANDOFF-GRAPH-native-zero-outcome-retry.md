# GRAPH: native retry after a proven non-publication

Status: ACTIVE. Owner: PRIME runtime repair/cleanup stewardship.
Base: origin/main@851586899f3274db1b68a47914ac021e60438e4c (merged2060).
Branch: codex/native-zero-outcome-retry; reuse buddy-context-loop.
Topology: parallel-independent of2062@500edc4a2d44c8aba2db1ea8e8147a043478813c
(extract_promote_ops/handoffs only). Predecessor2060 is merged/source-qualified;
its runtime delivery remains queued. No concurrent writer of this successor's
paths. Runtime delivery stays serial, after ADVERSARY releases693e comparison.

## Outcome and existing owners

Exact7d48 ordinary native lifecycle reproduction: first publication fails before
any write; native recover proves no receipt and unchanged parent. Governed retry
then reconstructs through the deleted filesystem producer and falsely reports
integrity failure. Preserve original evidence in private
threat-native-zero-outcome-boundary-red.{json,log}.

Use the already selected WorldGraphAuthority for head/context, publication and
recovery. Reconstruct against its exact retained parent with existing context
adapter; dispatch the same idempotent authority operation after current identity,
publication operation, sealed contribution and durable retry admission checks.
Adapt the native receipt through the existing owner and retain native child
verification/persistence. No Buddy merge callback or legacy lookup for retry.
Do not add a retry budget: keep the existing one governed recovery retry policy.

## Exclusive expected writes

- apps/live_control_server/services/threat_publication_commits.py
- tests/test_cutover_threat_authority_port.py
- Docs/Plans/HANDOFF-GRAPH-native-zero-outcome-retry.md
- Docs/Plans/HANDOFF-GRAPH-native-retained-threat-verification.md

The predecessor records its actual merged/pending-delivery status, never falsely
deployed. No broad legacy reconciler/hook/signature removal, registry-file work,
Gold/source/manual Graph repair, model, provider, primary data, schema or deps.

## Failure cases and validation

Extend the existing ordinary native lifecycle controls, without Cartesian test
explosion: publication failure before commit, lost response after commit, unavailable
recovery, advanced parent, second unknown attempt before/after commit and recovery
unavailability. Assert stable operation ID, known committed child retention,
native receipt recovery, no republish after recovered commit, no third dispatch,
and truthful pending/uncommitted/verified results. Preserve existing verification
positive/failed/unavailable/parent-unavailable cases and identity/selection checks.
Capture red before fix, run owning native authority/commit/proposal/confirmation
cohort, Ruff/diff and inspect only changed runtime functions. Independently review,
require CI and exact main integration/actual merge approval, then conserved runtime
delivery after explicit evaluation release. Synthetic tests are not DB proof.

## Author evidence

Captured original7d48 frontdoor failure, then formal regression red5failed/8passed
(17other authority tests deselected), including unavailable exactparent. Afterfix,
60owning authority/commit/proposal/scopedguard/confirmation tests pass with1 DB
integration deselected and inherited schema warning. Stable native operation ID,
actor/selection/parent, no duplicate publish after recovered commit and no third
dispatch asserted. Source/test Ruff and diff checks pass. Only _maybe_retry and
its two call sites in confirm_threat_publication change among runtime functions.
Private native-zero-outcome-retry-{red,red-v2,green}.log/author.json preserveproof.
Independent review, CI, actualmain/merge qualification and delivery outstanding.
