# PLAN: Accept proposals at an offered editor placement

Active independent frontend slice on codex/plan-proposal-placement-receipt,
based on 9e5aaeb6f. The Conks rehearsal goal authorizes fixing the mounted
Plan review blocker. The PDF upload, Event, activation and citation PRs
remain in their existing lanes. This slice depends on the existing
Plan placement catalog and has no database, provider or deployment change.

The live Conks response selected an offered page boundary, but the editor
required equality to the original caret. Reconstruct the allowed boundary
from the original capture and the offered entry. Check its digest and
retain all existing proposal and saved Plan checks. Reject an altered
capture even if the response hashes it consistently.

Write scope covers WorldPlanAgentConversation.tsx, its mounted test in
PlanSurfacePage.test.tsx and this brief. Verify ordinary caret and offered
boundary application, an altered boundary rejection, and the existing
local frontend contracts before delivery.
