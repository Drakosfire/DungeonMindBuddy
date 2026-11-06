# INGEST: recap faithfulness policy message role

Status: ACTIVE experimental producer slice; no quality improvement claimed.

## Outcome and invariant

Test whether placing the exact existing generic source-faithfulness policy once
in the system message improves standard-v2 recap adherence. Transfer text only:
no new/duplicated rules, corpus names, source edits, task/coverage loss, schema,
pass, provider, allocation or fallback. Worldbuilding and encounter-preview
messages remain unchanged. Renderer-only tests are insufficient: test actual
seven-pass client dispatch and preservation of untrusted source policy echoes.

## Authority / lane / topology

Root owns design and implementation under the active C1S1–10 goal. Independent
subagent critique `0ee32b1566d6c7a4ddb132092feaea4d17ac17acfb77a1300ded18b61776fd6c`
conditionally supports the role-only experiment. Exact retained replay audit
`62371419930f37fa26c4defd478f0593ad9c83ecab3500f4ad6929c9c4f57516`
proved all fourteen S5/S8 request hashes, including the existing policy. Transport
review `179805278a9f64924df5039fcd6160a5755a752a510eb3d6421989d7e566499a`
found no dropped parameters. Upstream compliance is unproven.

Branch `codex/ingest-recap-policy-role`, stacked on #2149 exact head
`857093a2263053b5c6ab30423262be03f1fe55bf` (#2149); merge/rebase order
#2145 → #2149 → this experiment. #2145 depends on #2144/#2131. Shared evaluator #2146 is independent host tooling.
No overlap with BUILD #2147, checked before activation. Prior rejected prompt
experiments #2140/#2143 are not inherited. No merge/deployment authority.

## Expected exclusive writes

- src/graph_memory/extraction/recap_extraction_profile.py
- src/graph_memory/extraction/category_candidate_graph_extractor.py
- tests/test_recap_policy_role.py
- this handoff

No model calls, APP/native writes, runtime allocation or live evaluator dispatch
from implementation/testing. Synthetic tests only. Fresh actual evaluations need
pinned reviewed runtime/tooling/source/ordinary name preflight and normal product
accounting; no arbitrary caps. Same-model current controls are required for any
causal claim; historical usage comparisons remain descriptive.

## Design / failure cases / validation

Keep canonical profile and standalone renderer semantics intact. A transient view
of the same profile removes only the trusted common policy from pass instructions
before message rendering; the extraction loop sends it once in system. Never
search/replace untrusted source or node-inventory text. Preserve pass-specific
rules, coverage, evidence, source packets and actor identity hints.

Test all seven actual dispatches, role-only byte delta, policy-looking source
preservation, canonical profile immutability, Worldbuilding/preview parity and
recap evidence/schema regressions. Inspect cumulative diff; independent exact-head
review; commit/push/open the assigned PR. Actual full Gold/completeness/precision,
positive knowledge preservation, cost and attribution must be assessed before
accepting the hypothesis. Failed experiments remain evidence, not default code.

## Adopted predecessor and renewed comparison boundary

The original control found cross-pass node-ID collisions. Repair #2149 now has
independent code/runtime/actual-ingestion verification, including 67 unique IDs
and 38 exact raw-to-final endpoints in fresh S8 run
6f132f6b-4d3d-4f2f-b3fc-5edf994d3834. Technical review SHA256
e74f3fd170ad59dd38ef674e6ae85fa7a07473f40dcf893a81b24e4df076afb7.
Full semantic review remains HOLD (all167 criteria/all117 records), SHA256
3b2e462d41a62a12efa4cd45d977624e6250ed9969cd15f9a2dca4e09ce94fe5.
Root adopts this code predecessor and transfers the two experimental production
paths back to this serial lane; the repair PR receives no concurrent edits.

Both comparison arms must contain the reviewed ID repair. No earlier unfixed
control may establish a causal role comparison. Preserve the failed control and
all Gold unchanged. This remains an unproven role-only hypothesis; no new rules,
corpus-specific guidance or publication of unsupported claims are authorized.
