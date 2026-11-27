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
native-Core source-required control was subsequently exercised as described below.

## Selected native source control

Case 493 supplied an explicitly selected native text section and an unrelated
synthetic App-page distractor. Its answer was factually correct, but the
anchored-discussion writer format did not permit a citation. Case 496 repeated
the development control against serving-port head
`b8d5caf41d1640a9ebc06b2d9206dcf5530d036a`; independent assessment found the
answer correct and its native-body citation bound to the supplied source,
revision, section and excerpt. Both cases used the same fixture and are not an
independent held-out comparison. The fixture and private rubric remain in the
owned local evidence directory, with SHA-256 pins
`ceecaee5ddeaad791ccafbba911e5b585e30519529481915e0fe410b4b8dff48` and
`50ca6c9dd2c89d74300bd128599194647950c911a1b5bf142d3ea7e431ba86c7`.

Case 496 observed native source preparation, a Graph query, selected-source
read and native body open, plus related App catalog discovery. These probes are
partial: they do not prove whether the distractor was materialized, a complete
acquisition count, or the absence of other activity. Four controller requests
and the writer request were independently audited before submission. Its
124.72-second elapsed time includes manual audit pauses and is not a latency
comparison.

The citation-capable format was merged in [#4954](https://github.com/Drakosfire/DungeonMindBuddy/pull/4954).
A reader-first compatibility release was deployed in
[run 45989643077](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/45989643077),
then the writer was deployed in [run 45990518822](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/45990518822)
as serving revision `c3f58d55b7df156ab101ed2b607a8309b502c74b`. The staged and
live identities, readiness and signed-out authentication checks passed.
In the signed-in long chat, a creative context-only request produced three
names; its trace showed 17.1 seconds to a validated reply and no captured Graph
crawler replay, but does not establish complete acquisition coverage. A
saved-page question produced a supported citation that reopened and persisted
across reload; its trace showed 14.8 seconds to a validated reply. These are
individual observations, not latency distributions. The native Core binding
was verified in the isolated replay, not through that saved-page UI check.

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

## Reconstructed Shepherd and long-chat development replays

On the existing owned App clone and read-only Core, three serial synthetic
captures used product candidate `0b20da53585e3487fca103a09b78473c69c0c58f`
(the tree of merged reader [#4997](https://github.com/Drakosfire/DungeonMindBuddy/pull/4997))
and the negative-evaluator code at [#5000](https://github.com/Drakosfire/DungeonMindBuddy/pull/5000).
The evaluator subtree was unchanged at main `0ca80b0d4ccb3a28955d22edd18b7c5df28c1d30`.
The candidate was not deployed for these captures. Main's App head was `0201`
at that revision, while the retained clone was on the serving lineage's `0214`;
these are serving-candidate observations, not a replay of main's Build changes.
The App owner and workers remained serial, and no new database was created.

| Development case | Result independently assessed | Observed related catalog / materialization attempts | Native-Graph probe records |
| --- | --- | --- | --- |
| Reconstructed Shepherd naming, case 716 | Ten distinct names; response used supplied setting and treated suggestions as creative | 0 / 0 | 0 |
| Sixty-exchange reuse, case 719 | Correctly recalled the toll and collector from the first exchange | 0 / 0 | 0 |
| Previously exposed H5 saved-note control, case 721 | Correct source-supported answer, preserving the note's draft status | 1 / 1 | 0 |

For the long-chat case, independently audited controller and writer requests
contained all 60 exchanges and the exact question. All three answers returned
HTTP 200; primary pages and the fixture-related pages remained stable. In the
source-required control, the cited claim's World, document, revision and digest
matched the returned materialization and frozen fixture. A subsequent read-only,
locally authenticated request to the ordinary related-page route reopened the
exact cited text; a different read ID returned 409 (case 724). This is local
route evidence, not a hosted signed-in browser check.

The three POST probes are partial. Zero observed entries do not establish zero
acquisition, and generic SQL starts are not source-read counts. Each controller
and writer request was paused for a separate prompt-boundary audit. Captured
HTTP times were 61.40, 71.32 and 116.34 seconds respectively, including those
pauses; they are not latency samples or a before/after comparison. Cases 716
and 719 use rebuilt synthetic identities, and all three use synthetic editor
snapshots and a mixed evaluator/serving-runner import arrangement. Complete
import and environment qualification, complete acquisition coverage, current
main behavior, independent held-out qualification and hosted app verification
remain open. Case 721 is an already exposed control, not fresh held-out evidence.

The exact manifests, source and fixture pins, audit receipts, responses, probes,
failed preflight attempts and local citation check are retained under
`/home/drakosfire/Projects/.codex/buddy-check.current-page-owner.ssCukO/owner/`
in cases 714–724. The retained App clone is still needed for
follow-up work; its owner has not accepted or abandoned the workstream.
