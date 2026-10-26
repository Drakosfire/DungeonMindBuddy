# BUILD: proposal destination consistency

## Authority and bounded scope

PRIME is design/implementation owner under the operator's connected-authoring goal.
Serial topology; one PR from fetched Buddy main130a082b8 in the existing
buddy-context-loop checkout. No new checkout, service, port or data store. #1764
remains parked. No concurrent implementation owns these paths at re-anchor.

This slice closes the writer's ability to acknowledge a different requested page
only in assumptions while producing an actionable current-page proposal. It does
not claim to fix requested-work routing or complete connected-page dogfood.
The retained failure selected current-page writing; the writer explicitly noted
that the request named another destination. Current output admission accepts it.
Seven simple synthetic routing contrasts passed and did not reproduce the failure.
Exact retained replay awaits explicit authorization following automatic review's
private-payload rejection. No private story/trace evidence belongs in this PR.

## Invariant and critique

The existing requested-work resolution remains the only semantic routing authority.
A writer cannot change its frozen operation, placement, source or review kind.
Add a required closed destination disposition to the generation-only proposal
output: current_page, different_page, unresolved. This expresses consistency with
the captured target, not a new classifier, a page ID or permission to redirect.
Different or unresolved disposition refuses before proposed/ready. Missing, extra
or invalid wire fields refuse. No old-output execution fallback is introduced.

Successful persisted BuildGeneratedProposal records keep their existing shape;
retained proposals remain readable and editable. The exact received raw response
remains diagnostic evidence under existing lifecycle ownership, never an editable
proposal on refusal. Preserve request/action identity, newer drafts, source state,
retry/unknown-outcome semantics and parent authorizations. No automatic alternate
route, second writer, new page, publication, resend or source Save occurs.

A precise host-owned failure code must remain inspectable on the proposal result;
never infer destination mismatch by parsing free-form assumptions or exception
messages. A generic stopped reply must not be relabeled as known-not-sent.
A new-page request must subsequently enter the existing connected-page review in a
fresh deliberately authorized turn. That routing correction and primary-page
origin binding are separate remaining destination work, not silently added here.

Independent critique identified the above boundaries and rejected a proposal that
would treat disposition as a router. Independent review cleared this bounded design before activation, requiring a
generation-only wire DTO and preservation of the exact host refusal code. PRIME
activates only this safeguard; review exact cumulative implementation afterward.

## Expected write lease

- This handoff and HANDOFF-AGENT-authored-node-context.md, only to settle delivered
  predecessor #1788 and clarify this serial scope.
- apps/live_control_server/services/build_document_proposal.py: generation-only
  strict output schema, target guidance, admission and exact typed refusal code.
- tests/test_build_document_proposal.py and tests/test_build_proposal_shared_writer.py:
  actual guarded SDK/APP/refusal lifecycle, no ready preview/proposal/no resend.
- Existing proposal-producing test transports only as required to emit the new
  wire disposition; the exact additional fixture is tests/test_agent_build_jev_ordinary_harness.py.

No stored proposal model, database migration, UI layout, classifier, source
publication or Core/GE change. If a required invariant needs another owner/path,
return to design before extending this lease.

## Verification and delivery gate

Prove normal current-page output; different/unresolved/missing/invalid disposition;
strict prepared-schema authorization; retained raw evidence with zero actionable
proposal/ready on refusal; one physical request and unchanged replay; existing
stored proposal readback. Test the owner and parent SDK/APP boundary, not just a
parser. Frozen response fixtures are synthetic, not semantic provider acceptance.
Inspect cumulative diff, obtain independent Bugbot review, push/open the assigned
PR; PRIME merge and protected API delivery require the applicable gates. Ordinary
new-page routing/creative acceptance remains explicitly unfinished.
