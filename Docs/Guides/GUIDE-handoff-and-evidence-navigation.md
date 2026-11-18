# Finding current work and historical evidence

Buddy has a large Plans collection because handoffs also preserve the history of
completed slices. A filename, a placement on `main`, or an `ACTIVE` label in an
old document is not by itself an assignment to start work. The repository's
[agent policy](../../AGENTS.md) and the explicit current assignment govern how
to establish authority and ownership.

## Before taking a slice

1. Re-anchor on the remote default branch and inspect relevant open PRs and
   active work, including paths and external resources that could collide.
2. Find the explicitly authorized, pinned handoff or bounded assignment. It may
   live on `main`, a branch, a PR or another durable ref. Check the intended
   outcome, base, write set, dependencies, topology and verification before
   editing. A `BLOCKED` design does not allocate a write lease.
3. Check the assignment against present evidence: was its predecessor merged,
   was the slice superseded or completed, and does another open lane own a
   needed path? Use the PR and Git history at the relevant exact revisions, not
   just the status line. If required scope exceeds the lease, resolve ownership
   under the applicable assignment before editing.
4. Assignments name responsibilities for the work at hand. Do not infer a
   standing role or a new dispatch from older process documents or old handoff
   language. Explicit user instructions and [AGENTS.md](../../AGENTS.md) govern
   over conflicting legacy material.

A historical handoff can still explain a decision, scope or verification result.
It does not silently authorize a rerun, a merge, provider calls, or use of
private campaign inputs. Repository links and commit pins help locate evidence;
a hash or a summary alone does not reproduce a missing private artifact.

## Follow an evidence trail

Start at the owning contract or report, note its date and exact source revision,
then follow its links to the implementation, tests, receipt and original inputs
where available. Separate a proposal from implemented behavior, a reported test
from one you ran, and a merged change from an observed deployment. If an input,
receipt or environment is missing, say which conclusion it limits rather than
filling the gap with a newer artifact.

For examples of a bounded accepted decision and its limitations, see the
[ingestion baseline and retrieval history](../Reports/REPORT-ingestion-baseline-and-retrieval-history-2026-11-07.md).
The [lab guide](../../evals/README.md) routes to preserved experiments and
warns about paid providers and private sources. The [documentation map](../README.md)
links current domain guides and explains the non-authoritative export copies.
