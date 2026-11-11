# Build heading target probe

ACTIVE · PRIME · serial · branch codex/build-heading-target-probe from 1b5e87418.
Reuse the buddy-context-loop checkout and its existing Python environment.
Write lease: this handoff, evals/buddy_benchmark/heading_target_probe.py and
tests/test_heading_target_probe.py. No overlap with the open Build document
discovery or layered map backlog PRs. No runtime, database or UI lease.

Prove one heading-only Jev decision can nominate an exact saved passage. Reuse
the native Markdown heading catalog and exact saved-section reader. Project
only request text, page titles, headings and request-local aliases. Require a
high-scoring unique choice; surface the selected passage as read-only review
context. Abstain on ties, malformed decisions and no clear destination.

Use synthetic pages for the live TypeSafe comparison. One request per case,
no retry or writer call. Verify the wire projection, exact passage selection
and abstention locally. The production Build adoption is a separate slice
after reviewing the measured result and the destination binding contract.

## Synthetic result

Three live decisions on jev-1.14.0, with four offered headings and no page
bodies in the request state. The clear request selected Mothfen → Watch at
0.97 and returned the exact two-line passage. The ambiguous Trade request's
highest score was 0.59, so the host returned no destination. The missing
Underground Tunnels request selected none. Wall times were 0.394, 0.179 and
0.148 seconds respectively. The provider returned no token usage. The 0.90
cutoff is an experiment setting. A larger heading catalog and indirect
requests remain unmeasured.

## Follow-up benchmark

The heading-only probe produced 7/7 correct destinations and 12/15 correct
abstentions on 22 synthetic trials. The three false positives were a planning
question, a draft requested in chat, and a move between pages. In a four-case
comparison, the existing Build intent menu still classified the chat draft as
page writing.

The locked probe asks one short intent question and one heading question in
the same call. It opens a preview only if both scores reach 0.90. This setting
passed 11/11 live cases with 4 or 34 headings, including all three original
false positives at 34 headings. Calls took 0.156–0.257 seconds. The larger
planning question still scored 0.88 for intent and 0.95 for the destination,
so the result depends on the host guard. The lowest passing edit intent score
was 0.91. These scores do not establish a calibrated production threshold.
The provider did not report token usage. The probe does not authorize writes.
