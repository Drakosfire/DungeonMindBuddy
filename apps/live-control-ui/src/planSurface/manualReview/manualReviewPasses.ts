export const NODE_PASS_NAMES = [
  "actor_pass",
  "location_pass",
  "collective_pass",
  "object_pass",
  "thread_pass",
] as const;

export const EDGE_PASS_NAME = "edge_pass" as const;

export type ManualReviewPassId = (typeof NODE_PASS_NAMES)[number] | typeof EDGE_PASS_NAME;

export const PASS_LABELS: Record<ManualReviewPassId, string> = {
  actor_pass: "Actor",
  location_pass: "Location",
  collective_pass: "Collective",
  object_pass: "Object",
  thread_pass: "Thread",
  edge_pass: "Edge",
};

export const BASELINE_VARIANT = "baseline";
export const ASSISTED_VARIANT = "edge_and_node_packet";

export const VARIANT_LABELS: Record<string, string> = {
  [BASELINE_VARIANT]: "Baseline (no vocabulary)",
  [ASSISTED_VARIANT]: "Node + edge vocabulary",
};
