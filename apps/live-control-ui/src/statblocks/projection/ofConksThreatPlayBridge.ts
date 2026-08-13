import type { StoredStatblockDraftRecord } from "../../api/types";

const OF_CONKS_THREAT_PLAY_ARTIFACT_BY_KEY: Readonly<Record<string, string>> = {
  "grotesque-tree": "of-conks-grotesque-tree",
  guardian: "of-conks-guardian",
  caretakers: "of-conks-caretakers-twig-blight",
};

function normalizeThreatNodeKey(threatNodeId: string): string {
  const trimmed = threatNodeId.trim();
  if (trimmed.startsWith("threat:")) {
    return trimmed.slice("threat:".length);
  }
  return trimmed;
}

export function playArtifactIdForThreatNode(threatNodeId: string): string | null {
  const key = normalizeThreatNodeKey(threatNodeId);
  return OF_CONKS_THREAT_PLAY_ARTIFACT_BY_KEY[key] ?? null;
}

export type OfConksPlayDraftSummary = {
  artifactId: string;
  title: string;
  markdown: string;
  armorClass: string | number | null;
  hitPoints: string | number | null;
  speed: string | null;
  challengeRating: string | null;
  tactics: string[];
  primaryActions: string[];
};

export function summaryFromWorkbenchRecord(
  record: StoredStatblockDraftRecord,
): OfConksPlayDraftSummary {
  const { artifact } = record;
  const combat = artifact.combat_defaults;
  const structured = artifact.structured_statblock;
  const rawCr = structured.challenge_rating;
  const challengeRating =
    typeof rawCr === "string" || typeof rawCr === "number" ? String(rawCr) : null;

  return {
    artifactId: record.artifact_id,
    title: record.title,
    markdown: artifact.markdown,
    armorClass: combat.armor_class ?? null,
    hitPoints: combat.hit_points ?? null,
    speed: combat.speed ?? combat.speed_summary ?? null,
    challengeRating,
    tactics: combat.suggested_tactics ?? [],
    primaryActions: combat.primary_actions ?? [],
  };
}
