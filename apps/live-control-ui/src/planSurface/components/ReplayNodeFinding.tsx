import type { BuddyTurnContextTrace } from "../../api/buddyContextTraceTypes";
import { RecordedReplayAssertionContent, useRecordedReplayAssertion } from "./BuddyReplayAssertion";
import type { RetrievalStep } from "./BuddyRetrievalReplay";

export function ReplayNodeFinding({ trace, step, assertionId, nodeId }: {
  trace: BuddyTurnContextTrace;
  step: RetrievalStep;
  assertionId: string;
  nodeId: string;
}) {
  const read = useRecordedReplayAssertion({ trace, step, assertionId, open: true });
  const assertion = read?.assertion;
  if (!read) return <p role="status">Reading recorded evidence…</p>;
  if (!assertion || assertion.subject_entity_id !== nodeId) return <p>Recorded evidence is unavailable.</p>;
  const value = assertion.value;
  if (assertion.predicate === "dungeonbuddy:summary" && value && typeof value === "object"
      && "kind" in value && value.kind === "literal" && "value" in value && typeof value.value === "string") {
    return <div>
      <p>{value.value}</p>
      <details><summary>Open exact evidence</summary><RecordedReplayAssertionContent read={read} /></details>
    </div>;
  }
  return null;
}
