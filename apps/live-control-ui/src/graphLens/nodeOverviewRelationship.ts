const verbs: Readonly<Record<string, string>> = {
  parent_of: "is a parent of",
  child_of: "is a child of",
  member_of: "is a member of",
  leads: "leads",
  commands: "commands",
  works_with: "works with",
  cooperates_with: "cooperates with",
  located_in: "is located in",
  travels_to: "travels to",
  threatens: "threatens",
  holds: "holds",
  knows_about: "knows about",
  aware_of: "is aware of",
  participates_in: "participates in",
  occurred_at: "occurred at",
};

export function nodeOverviewRelationship(predicate: string, subject: string, object: string): string | undefined {
  const [namespace, relation, extra] = predicate.split(":");
  if (extra !== undefined || !["dungeonbuddy", "dungeonbuddy.custom", "dnd5e"].includes(namespace)) return;
  if (!Object.hasOwn(verbs, relation)) return;
  return `${subject} ${verbs[relation]} ${object}.`;
}
