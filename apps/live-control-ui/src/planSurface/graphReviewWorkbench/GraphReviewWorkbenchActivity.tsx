import type { GraphReviewActivity } from "./graphReviewActivity";

interface GraphReviewWorkbenchActivityProps {
  activity: GraphReviewActivity | null;
}

export function GraphReviewWorkbenchActivity({
  activity,
}: GraphReviewWorkbenchActivityProps) {
  if (!activity) return null;

  return (
    <span
      className={[
        "graph-review-activity",
        activity.busy ? "graph-review-activity--busy" : "graph-review-activity--ready",
        `graph-review-activity--${activity.phase}`,
      ].join(" ")}
      data-testid="graph-review-activity"
      data-phase={activity.phase}
      role="status"
      aria-live="polite"
      aria-busy={activity.busy ? true : undefined}
    >
      <span className="graph-review-activity__dot" aria-hidden="true" />
      <span className="graph-review-activity__message">{activity.message}</span>
    </span>
  );
}
