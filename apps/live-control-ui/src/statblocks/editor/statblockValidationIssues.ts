import type {
  ValidationIssueV1,
  ValidationStatus,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import type { ValidationReceiptStatus } from "./statblockEditorState";

export type PartitionedValidationIssues = {
  fieldIssues: ValidationIssueV1[];
  globalIssues: ValidationIssueV1[];
};

export type SeverityBuckets = {
  errors: ValidationIssueV1[];
  warnings: ValidationIssueV1[];
  infos: ValidationIssueV1[];
};

export type FieldPathToken =
  | { kind: "prop"; name: string }
  | { kind: "index"; index: number };

/**
 * Parse a Server field_path into exact tokens.
 * Returns null when the syntax is malformed (no normalization/guessing).
 *
 * Accepted forms: `a.b`, `rule_elements[0].mechanic`, `abilities.strength`
 */
export function parseFieldPath(path: string): FieldPathToken[] | null {
  const trimmed = path.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith(".") || trimmed.endsWith(".") || trimmed.includes("..")) return null;

  const tokens: FieldPathToken[] = [];
  let i = 0;
  while (i < trimmed.length) {
    if (trimmed[i] === ".") {
      i += 1;
      if (i >= trimmed.length || trimmed[i] === "." || trimmed[i] === "[") return null;
      continue;
    }

    if (trimmed[i] === "[") {
      if (tokens.length === 0) return null;
      const close = trimmed.indexOf("]", i);
      if (close < 0) return null;
      const raw = trimmed.slice(i + 1, close);
      if (!/^\d+$/.test(raw)) return null;
      tokens.push({ kind: "index", index: Number(raw) });
      i = close + 1;
      continue;
    }

    // property name
    let j = i;
    while (j < trimmed.length && trimmed[j] !== "." && trimmed[j] !== "[") {
      j += 1;
    }
    const name = trimmed.slice(i, j);
    if (!name || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) return null;
    tokens.push({ kind: "prop", name });
    i = j;
  }

  return tokens.length > 0 ? tokens : null;
}

/** True when every token resolves against the current working-copy value. */
export function resolveFieldPathAgainstWorkingCopy(
  workingCopy: unknown,
  tokens: FieldPathToken[],
): boolean {
  let current: unknown = workingCopy;
  for (const token of tokens) {
    if (token.kind === "prop") {
      if (current === null || typeof current !== "object" || Array.isArray(current)) {
        return false;
      }
      if (!Object.prototype.hasOwnProperty.call(current, token.name)) {
        return false;
      }
      current = (current as Record<string, unknown>)[token.name];
      continue;
    }
    if (!Array.isArray(current)) return false;
    if (token.index < 0 || token.index >= current.length) return false;
    current = current[token.index];
  }
  return true;
}

/**
 * Partition issues into field vs global.
 * Only honestly resolvable paths against the current working copy are field issues.
 * Empty, malformed, unknown, future, and out-of-range paths are global (never dropped).
 */
export function partitionValidationIssuesByPath(
  issues: ValidationIssueV1[] | null | undefined,
  workingCopy: unknown,
): PartitionedValidationIssues {
  const fieldIssues: ValidationIssueV1[] = [];
  const globalIssues: ValidationIssueV1[] = [];
  for (const issue of issues ?? []) {
    const rawPath = typeof issue.field_path === "string" ? issue.field_path : "";
    const tokens = parseFieldPath(rawPath);
    if (tokens && resolveFieldPathAgainstWorkingCopy(workingCopy, tokens)) {
      fieldIssues.push(issue);
    } else {
      globalIssues.push(issue);
    }
  }
  return { fieldIssues, globalIssues };
}

/** Preserve Server severities exactly: info | warning | error. */
export function splitIssuesBySeverity(issues: ValidationIssueV1[]): SeverityBuckets {
  return {
    errors: issues.filter((issue) => issue.severity === "error"),
    warnings: issues.filter((issue) => issue.severity === "warning"),
    infos: issues.filter((issue) => issue.severity === "info"),
  };
}

/** Map Server ValidationStatus onto editor receipt-bearing UI statuses. */
export function mapServerValidationStatus(
  status: ValidationStatus,
): ValidationReceiptStatus {
  switch (status) {
    case "valid":
      return "validated";
    case "warnings":
      return "validated_with_warnings";
    case "invalid":
      return "validated_with_errors";
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}
