# Negative-retrieval H5 and release observations

The frozen H5 set was independently authored before its first replay, but its
author knew the implementation and previous cases. It is not a blinded study.
It contains a creative negative, a 48-exchange context-reuse negative and a
related App page source-required control. Fixture SHA-256:
`163267cab2435e627f3be92257da1828605614ea8e26828f8519f24513829ca5`;
private rubric SHA-256:
`a82ffe4bf495c3a60918c63055b7f04c04aa25b020b8c008d0480f3175a55f83`.
Private rubrics and host metadata were excluded from audited model requests.

The creative baseline, case 382, ran on serving revision
`9ec881f7e3bc091a2ea9d2a4815ab0b71fd6718d`. All eight suggestions violated
the two-word constraint; both audited model requests had received it. This
case was promoted to development after the failure. An effort adjustment for
admitted Build discussions was merged in [#4941](https://github.com/Drakosfire/DungeonMindBuddy/pull/4941)
and ported to serving in [#4943](https://github.com/Drakosfire/DungeonMindBuddy/pull/4943).
The final two cases had not previously been replayed; their independent author
also reviewed the answers and exact request wires.

| Case | Captured case | Independent quality review | Observed related catalog / materialization attempts | Classified saved-revision body attempts | Unclassified SQL starts |
| --- | --- | --- | --- | ---: | ---: |
| Creative baseline | 382 | Failed word-count constraint | 0 / 0 | 1 | 240 |
| Creative development replay | 400 | Passed | 0 / 0 | 1 | 235 |
| Long-context negative | 403 | Passed; both wires preserved 48 exchanges | 0 / 0 | 1 | 247 |
| Related-source control | 406 | Passed; citation matched and supported by returned revision | 1 / 1 | 2 | 415 |

Counts are partial attempted operations from different owners and must not be
added as distinct source counts. The saved-revision count includes primary-page
validation. The independent reviewer matched the related citation to the
fixture and returned materialization by World, document, revision and body
digest. All four fixture bindings passed. All four offline reports remain
**unproven**: acquisition completeness and capture-environment qualification
are missing. Absence of an observed call is not proof of no acquisition. The
native-Core source-required control is still missing.

Case 400 ran against exact serving-port head
`7e1327151d75c9405ca183e36b2353bfad57881d`; the deployed merge has the same
tree. It took 4.96 seconds for one instrumented local request. Cases 403 and
406 took 73.69 and 93.32 seconds including manual request-audit pauses, so
those values are not meaningful latency samples. A separate matched local
development pair measured 3.65 seconds at low effort and 4.10 seconds at medium
effort; single observations do not establish a latency distribution.

The port was published in [run 45958072782](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/45958072782)
and deployed in [run 45958510211](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/45958510211)
as serving revision `a3b765cf7980f5c191b810c3efe0f549ef844676` and image ID
`sha256:79cc3f6048d960567e94600e254bc97cb23db8d5ec08f0315cccaf91146d529a`.
Staged and live identities matched; public readiness and signed-out auth checks
passed. In the signed-in app, a fresh synthetic creative request returned eight
distinct compliant names, and a saved-page question returned an accurate answer
with a reopened supporting citation. The UI trace showed 8.7 and 11.7 seconds
to validated replies, respectively. Those partial traces do not establish zero
acquisition or end-to-end latency.

Synthetic fixtures, manifests, requests, responses, reviews and reports remain
host-local under `/home/drakosfire/Projects/.codex/buddy-check.current-page-owner.ssCukO`
and `/tmp/buddy-independent-heldout-h5-3h7_b1sh`. The existing owned App clone
and read-only Core were reused serially; no additional clone was created. This
record does not make the host-local artifacts portable or complete the goal.
