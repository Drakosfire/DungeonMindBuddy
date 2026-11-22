# DOGFOOD: create a lore page from retained conversation evidence

Status DELIVERED for the bounded destination-parser slice: PR #4402 merged as
`90b95f43f06f2e92d2fabe67872e9ef446c91f6e` after independent exact-head PASS.
Its implementation write lease is released. The full goal remains open;
the consuming [release-selection handoff](HANDOFF-DOGFOOD-aw10-release-selection.md)
owns serving adoption and records remaining latency and production evidence.

The operator explicitly authorized the Maelthor page, reuse of
already retrieved context without searching again, and fast execution in this
chat. This first serial implementation slice repairs the generic explicit
destination boundary; the full goal also requires actual Elderwyld page creation
and measured live reuse. A proposal or passing synthetic test is not completion.

## Lane and boundary

Branch `codex/dogfood-maelthor-context-reuse`, base
`ed5564f024ec941eb3447a4b23ea0407ee594590`, isolated checkout
`/home/drakosfire/Projects/.codex/79e2/DungeonMindBuddy`.
No unmerged behavioral parent. Serial delivery; no concurrent agent work.
Open AW10 benchmark PR #4017 owns its benchmark definition, not these runtime
paths. Re-anchored open PRs include no competing lore-page runtime lane.

Exclusive expected write set:

- `src/application_state/agent_conversation/lore_page_review.py`
- `tests/test_lore_page_review.py`
- `tests/test_surface_native_build_ordinary.py` (existing lore-page case only)
- this handoff

No service restart, ports, deployment, operator database migration, Graph write,
provider/model change or frontend change belongs to this slice. Verification
scratch and evidence: `/home/drakosfire/Projects/.codex/buddy-check.q9sCkN`.
Database checks use the repository's disposable session-template/per-test clones.

## Invariant and failure cases

An explicit named request using “the page” must bind the same exact destination
as “a page”. Its literal author instruction still owns the title. Foreign titles,
compound destinations, multiple requests and populated blank-page requests must
fail closed. This parser also gates waiting for the opening work choice before
eager Graph preparation. Conversation synthesis must retain the pending query,
admit prior exact citations, and never start new Graph preparation.

The supplied failed Maelthor turn selected the older research route and then
returned a lore proposal that cannot satisfy the literal parser. Subsequent
inspection verified the retained preceding evidence and found serving revision
`03055f248645c3a2bc67d2904825637b23687ada` lacks the merged conversation-reuse
choice. The article fix alone does not prove hosted route availability.

Independent review of exact head `d536c8e06ed976d829095bec14902b613c4462e4`
found no actionable issues and independently ran 38 parser tests. Real-provider
fresh-context acceptance created one populated Copperglass Watch page in a new
empty conversation, retained all supplied proposed details and the open
question, and independently reopened the committed page. Draft: 7.660 seconds;
confirmation/reopen: 58 milliseconds; repeated confirmation returned the same
receipt. This ordinary route prepared Graph/related-page context but read no
source bodies. Separately, three Maelthor reuse replays performed zero new
acquisition, retained exact citations, and saved/reopened one disposable page
each; their 10.983–14.385-second drafts still miss the 10-second target.

## Validation and remaining goal

Verify article variants and rejection guards, then the existing ordinary HTTP
conversation-synthesis case extended to “Create the page about Glass Regent”.
That case must reject any Graph preparation, carry prior exact citations through
durable completion, save/reopen one page, preserve open questions, reject stale
and wrong reviews, and return the same confirmation receipt on replay.
Run owning contracts from an isolated exact commit with locked Python dependencies;
inspect the cumulative diff, commit, push and open the implementation PR.

Then inspect the actual Elderwyld preceding conversation and deployed revision.
Use its retained evidence for the requested Maelthor page, with zero new source
acquisition. Measure ordinary draft latency (target <=10 seconds) and confirmation
to independent reopen against the supplied approximately 107-second failed turn.
Deployment/merge authority is separate. If further code is necessary, checkpoint
and allocate a bounded serial successor rather than expanding this write lease.
