/** Pure presentation helpers for typed statblock definitions. No canonical schema ownership. */

export type JsonRecord = Record<string, unknown>;

export function asRecord(value: unknown): JsonRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as JsonRecord)
    : null;
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function textOrNull(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

export function abilityModifier(score: unknown): string | null {
  if (typeof score !== "number" || !Number.isFinite(score)) return null;
  const mod = Math.floor((score - 10) / 2);
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

export function formatDistance(value: unknown): string | null {
  const record = asRecord(value);
  if (!record) return null;
  const amount = record.value ?? record.distance;
  const unit = textOrNull(record.unit) ?? "ft.";
  if (typeof amount === "number") return `${amount} ${unit}`;
  if (typeof amount === "string" && amount.trim()) return `${amount} ${unit}`;
  return null;
}

export function movementSummary(definition: JsonRecord): string {
  const movement = asRecord(definition.movement);
  const modes = asArray(movement?.modes);
  const parts = modes
    .map((mode) => {
      const record = asRecord(mode);
      if (!record) return null;
      const label = textOrNull(record.mode) ?? textOrNull(record.key) ?? "move";
      const distance = formatDistance(record.distance) ?? formatDistance(record);
      return distance ? `${label} ${distance}` : label;
    })
    .filter((part): part is string => Boolean(part));
  return parts.length ? parts.join(", ") : "—";
}

export function armorClassSummary(definition: JsonRecord): string {
  const defenses = asRecord(definition.defenses);
  const armorClasses = asArray(defenses?.armor_classes);
  const parts = armorClasses
    .map((entry) => {
      const record = asRecord(entry);
      if (!record) return null;
      const value = record.value;
      const label = textOrNull(record.label) ?? textOrNull(record.key);
      if (typeof value !== "number") return null;
      return label ? `${value} (${label})` : String(value);
    })
    .filter((part): part is string => Boolean(part));
  return parts.length ? parts.join(", ") : "—";
}

export function hitPointsSummary(definition: JsonRecord): string {
  const vitality = asRecord(definition.vitality);
  const hitPoints = asRecord(vitality?.hit_points);
  if (!hitPoints) return "—";
  if (typeof hitPoints.fixed_value === "number") return String(hitPoints.fixed_value);
  if (typeof hitPoints.displayed_average === "number") {
    const formula = asRecord(hitPoints.formula);
    if (formula && typeof formula.count === "number" && typeof formula.die === "number") {
      const modifier = typeof formula.modifier === "number" ? formula.modifier : 0;
      const modText = modifier >= 0 ? `+ ${modifier}` : `- ${Math.abs(modifier)}`;
      return `${hitPoints.displayed_average} (${formula.count}d${formula.die} ${modText})`;
    }
    return String(hitPoints.displayed_average);
  }
  return "—";
}

export interface RuleElementView {
  key: string;
  name: string;
  section: string;
  rulesText: string | null;
  summary: string | null;
  automationSupport: string | null;
  humanAdjudicated: boolean;
}

export function ruleElements(definition: JsonRecord): RuleElementView[] {
  return asArray(definition.rule_elements)
    .map((entry, index) => {
      const record = asRecord(entry);
      if (!record) return null;
      const automationSupport = textOrNull(record.automation_support);
      return {
        key: textOrNull(record.key) ?? `element-${index}`,
        name: textOrNull(record.name) ?? textOrNull(record.key) ?? `Element ${index + 1}`,
        section: textOrNull(record.section) ?? "other",
        rulesText: textOrNull(record.rules_text),
        summary: textOrNull(record.summary),
        automationSupport,
        humanAdjudicated: automationSupport === "human_adjudicated",
      };
    })
    .filter((entry): entry is RuleElementView => entry != null);
}

export interface ValidationIssueView {
  code: string;
  message: string;
  severity: "error" | "warning" | "info";
  fieldPath: string | null;
}

export function validationIssues(candidate: JsonRecord): ValidationIssueView[] {
  const receipt = asRecord(candidate.validation_receipt);
  return asArray(receipt?.issues)
    .map((issue) => {
      const record = asRecord(issue);
      if (!record) return null;
      const severityRaw = textOrNull(record.severity) ?? "info";
      const severity =
        severityRaw === "error" || severityRaw === "warning" ? severityRaw : "info";
      return {
        code: textOrNull(record.code) ?? "UNKNOWN",
        message: textOrNull(record.message) ?? "Validation issue",
        severity,
        fieldPath: textOrNull(record.field_path),
      };
    })
    .filter((entry): entry is ValidationIssueView => entry != null);
}
