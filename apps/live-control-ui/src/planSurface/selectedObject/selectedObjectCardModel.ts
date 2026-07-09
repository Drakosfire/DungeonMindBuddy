import type { ReferenceResolution } from "../reference/referenceResolver";

export type SelectedObjectKind =
  | "npc"
  | "location"
  | "statblock"
  | "roll-table"
  | "unknown";

export interface SelectedObjectField {
  label: string;
  value: string;
  priority?: "primary" | "secondary";
}

export interface SelectedObjectAction {
  id: string;
  label: string;
  disabled?: boolean;
  reason?: string;
  href?: string;
}

export type SelectedObjectActionIntent =
  | "expand"
  | "ingest"
  | "statblock_tool"
  | "statblock_selected"
  | "roll";

export interface SelectedObjectMetadata {
  refType: string;
  refId: string;
  dice?: string;
  corpusDisplayPath?: string;
  indexId?: string;
  artifactId?: string;
}

export interface SelectedObjectCardModel {
  status: "resolved" | "unresolved" | "error";
  kind: SelectedObjectKind;
  title: string;
  subtitle?: string;
  summary: string;
  sourcePath?: string;
  primaryFields: SelectedObjectField[];
  secondaryFields: SelectedObjectField[];
  actionIntents: SelectedObjectActionIntent[];
  metadata?: SelectedObjectMetadata;
  diagnostics?: string[];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object") return null;
  return value as Record<string, unknown>;
}

function pickString(item: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = item[key];
    if (value == null || value === "") continue;
    if (typeof value === "string" || typeof value === "number") {
      return String(value);
    }
  }
  return undefined;
}

function pickField(
  item: Record<string, unknown>,
  keys: string[],
  label: string,
  priority: "primary" | "secondary" = "primary",
): SelectedObjectField | null {
  const value = pickString(item, keys);
  if (!value) return null;
  return { label, value, priority };
}

function refTypeToKind(refType: string): SelectedObjectKind {
  if (refType === "npc") return "npc";
  if (refType === "location") return "location";
  if (refType === "statblock") return "statblock";
  if (refType === "roll-table") return "roll-table";
  return "unknown";
}

export function selectedObjectKindLabel(kind: SelectedObjectKind): string {
  switch (kind) {
    case "npc":
      return "NPC";
    case "location":
      return "Location";
    case "statblock":
      return "Statblock / threat";
    case "roll-table":
      return "Roll table";
    default:
      return "Reference";
  }
}

function gameSummaryForItem(kind: SelectedObjectKind, item: Record<string, unknown>): string {
  const direct = pickString(item, [
    "summary",
    "description",
    "game_summary",
    "table_note",
    "info_tag",
    "role",
    "role_tag",
  ]);
  if (direct) return direct;

  switch (kind) {
    case "npc":
      return "NPC reference resolved from corpus index.";
    case "location":
      return "Location reference resolved from corpus index.";
    case "statblock":
      return "Statblock reference resolved from corpus index.";
    case "roll-table":
      return "Roll table reference resolved from corpus index.";
    default:
      return "Reference resolved from corpus index.";
  }
}

function titleForItem(item: Record<string, unknown>, fallback: string): string {
  return pickString(item, ["title", "name"]) ?? fallback;
}

function npcFields(item: Record<string, unknown>): {
  primary: SelectedObjectField[];
  secondary: SelectedObjectField[];
} {
  const primary = [
    pickField(item, ["role", "npc_role"], "Role"),
    pickField(item, ["faction"], "Faction"),
    pickField(item, ["location", "settlement"], "Location"),
  ].filter((field): field is SelectedObjectField => field !== null);

  const secondary = [
    pickField(item, ["status", "canon_layer"], "Status", "secondary"),
    pickField(item, ["session", "section"], "Session", "secondary"),
  ].filter((field): field is SelectedObjectField => field !== null);

  return { primary, secondary };
}

function locationFields(item: Record<string, unknown>): {
  primary: SelectedObjectField[];
  secondary: SelectedObjectField[];
} {
  const primary = [
    pickField(item, ["settlement"], "Settlement"),
    pickField(item, ["region"], "Region"),
    pickField(item, ["district"], "District"),
    pickField(item, ["location_type"], "Type"),
  ].filter((field): field is SelectedObjectField => field !== null);

  const secondary = [
    pickField(item, ["session", "section"], "Session", "secondary"),
  ].filter((field): field is SelectedObjectField => field !== null);

  return { primary, secondary };
}

function statblockFields(item: Record<string, unknown>): {
  primary: SelectedObjectField[];
  secondary: SelectedObjectField[];
} {
  const primary = [
    pickField(item, ["creature_type"], "Creature type"),
    pickField(item, ["challenge_rating", "cr"], "CR"),
    pickField(item, ["armor_class", "ac"], "AC"),
    pickField(item, ["hit_points", "hp"], "HP"),
    pickField(item, ["role", "battlefield_role", "role_tag"], "Role"),
  ].filter((field): field is SelectedObjectField => field !== null);

  const secondary = [
    pickField(item, ["info_tag"], "Threat note", "secondary"),
  ].filter((field): field is SelectedObjectField => field !== null);

  return { primary, secondary };
}

function rollTableFields(item: Record<string, unknown>): {
  primary: SelectedObjectField[];
  secondary: SelectedObjectField[];
} {
  const primary = [
    pickField(item, ["table_id"], "Table id"),
    pickField(item, ["category"], "Category"),
    pickField(item, ["dice", "die"], "Dice"),
    pickField(item, ["row_count"], "Row count"),
  ].filter((field): field is SelectedObjectField => field !== null);

  return { primary, secondary: [] };
}

function fieldsForKind(
  kind: SelectedObjectKind,
  item: Record<string, unknown>,
): { primary: SelectedObjectField[]; secondary: SelectedObjectField[] } {
  switch (kind) {
    case "npc":
      return npcFields(item);
    case "location":
      return locationFields(item);
    case "statblock":
      return statblockFields(item);
    case "roll-table":
      return rollTableFields(item);
    default:
      return { primary: [], secondary: [] };
  }
}

function extractMetadata(
  kind: SelectedObjectKind,
  item: Record<string, unknown>,
  refType: string,
  refId: string,
): SelectedObjectMetadata {
  return {
    refType,
    refId,
    dice: kind === "roll-table" ? pickString(item, ["dice", "die"]) : undefined,
    corpusDisplayPath: pickString(item, ["corpus_display_path", "primary_doc_path", "hub_path"]),
    indexId: pickString(item, ["index_id"]),
    artifactId: pickString(item, ["artifact_id"]),
  };
}

function defaultActionIntents(
  kind: SelectedObjectKind,
  metadata?: SelectedObjectMetadata,
): SelectedObjectActionIntent[] {
  const intents: SelectedObjectActionIntent[] = ["expand", "ingest"];

  if (kind === "statblock") {
    intents.push(metadata?.artifactId ? "statblock_selected" : "statblock_tool");
  }

  if (kind === "roll-table" && metadata?.dice) {
    intents.push("roll");
  }

  return intents;
}

function unresolvedSummary(resolution: ReferenceResolution): string {
  if (resolution.ref.kind === "action") {
    return resolution.message;
  }
  if (resolution.ref.refType === "citation") {
    return "Citation resolver pending.";
  }
  if (resolution.status === "error") {
    return resolution.message;
  }
  return "Could not resolve this reference. Check spelling or review memory in /ingest.";
}

function unresolvedFields(resolution: ReferenceResolution): SelectedObjectField[] {
  const fields: SelectedObjectField[] = [
    { label: "Type", value: resolution.ref.refType, priority: "primary" },
    { label: "Id", value: resolution.ref.refId, priority: "primary" },
  ];
  if (resolution.status === "error") {
    fields.push({ label: "Error", value: resolution.message, priority: "secondary" });
  }
  return fields;
}

export function buildSelectedObjectCardModel(resolution: ReferenceResolution): SelectedObjectCardModel {
  const kind = refTypeToKind(resolution.ref.refType);

  if (resolution.status !== "resolved" || !resolution.item) {
    const isAction = resolution.ref.kind === "action";
    const isCitation = resolution.ref.refType === "citation";

    return {
      status: resolution.status === "error" ? "error" : "unresolved",
      kind: isAction || isCitation ? "unknown" : kind,
      title: isAction ? "Action placeholder" : resolution.ref.label,
      subtitle: isCitation ? "Citation" : isAction ? "Action" : selectedObjectKindLabel(kind),
      summary: unresolvedSummary(resolution),
      primaryFields: isAction || isCitation ? [] : unresolvedFields(resolution),
      secondaryFields: [],
      actionIntents: isAction ? [] : ["ingest"],
      metadata: isAction || isCitation
        ? undefined
        : {
            refType: resolution.ref.refType,
            refId: resolution.ref.refId,
          },
      diagnostics: resolution.status === "error" && resolution.message
        ? [resolution.message]
        : undefined,
    };
  }

  const item = asRecord(resolution.item)!;
  const { primary, secondary } = fieldsForKind(kind, item);
  const metadata = extractMetadata(kind, item, resolution.ref.refType, resolution.ref.refId);

  return {
    status: "resolved",
    kind,
    title: titleForItem(item, resolution.ref.label),
    subtitle: selectedObjectKindLabel(kind),
    summary: gameSummaryForItem(kind, item),
    sourcePath: resolution.sourcePath,
    primaryFields: primary,
    secondaryFields: secondary,
    actionIntents: defaultActionIntents(kind, metadata),
    metadata,
    diagnostics: resolution.message ? [resolution.message] : undefined,
  };
}
