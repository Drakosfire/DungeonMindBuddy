import { nodeOverviewRelationship } from "../../graphLens/nodeOverviewRelationship";
import type { BuddyTurnContextTrace } from "../../api/buddyContextTraceTypes";
import { RecordedReplayAssertionContent, useRecordedReplayAssertion } from "./BuddyReplayAssertion";
import type { RetrievalStep } from "./BuddyRetrievalReplay";

export function ReplayNodeFinding({ trace, step, assertionId, nodeId, nodeLabel, labelFor }: {
  trace: BuddyTurnContextTrace;
  step: RetrievalStep;
  assertionId: string;
  nodeId: string;
  nodeLabel: string;
  labelFor: (id: string) => string | undefined;
}) {
  const read = useRecordedReplayAssertion({ trace, step, assertionId, open: true });
  const assertion = read?.assertion;
  if (!read) return <p role="status">Reading recorded evidence…</p>;
  if (!assertion || assertion.subject_entity_id !== nodeId) return <p>Recorded evidence is unavailable.</p>;
  const value = assertion.value;
  let finding: string | undefined;
  if (value && typeof value === "object" && "kind" in value) {
    if (assertion.predicate === "dungeonbuddy:summary" && value.kind === "literal"
        && "value" in value && typeof value.value === "string") {
      finding = value.value.trim();
    } else if (value.kind === "entity_ref" && "entity_id" in value && typeof value.entity_id === "string") {
      const related = labelFor(value.entity_id);
      if (related) finding = nodeOverviewRelationship(assertion.predicate, nodeLabel, related);
    }
  }
  if (!finding) return null;
  const qualifications = assertion.metadata;
  return <div>
    {qualifications && <p className="graph-node-explorer__context">
      {[qualifications.claim_mode.replace(/^dungeonbuddy\.claim:/, ""), qualifications.epistemic_basis, qualifications.standing].join(" · ")}
    </p>}
    <p>{finding}</p>
    <details><summary>Open exact evidence</summary><RecordedReplayAssertionContent read={read} labelFor={id => id === nodeId ? nodeLabel : labelFor(id)} /></details>
  </div>;
}
