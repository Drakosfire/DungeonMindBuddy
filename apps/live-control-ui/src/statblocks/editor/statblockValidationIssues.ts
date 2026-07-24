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

type ParserState = "expect_prop" | "after_prop" | "after_index";

/**
 * Parse a Server field_path into exact tokens.
 * Returns null when the syntax is malformed (no normalization/guessing).
 *
 * Accepted forms: `a.b`, `rule_elements[0].mechanic`, `foo[0][1]`, `abilities.strength`
 *
 * Rejects: leading/trailing/internal whitespace, `]prop` without a dot,
 * empty segments, non-decimal indices, trailing dots.
 */
export function parseFieldPath(path: string): FieldPathToken[] | null {
  if (path.length === 0) return null;

  const tokens: FieldPathToken[] = [];
  let i = 0;
  let state: ParserState = "expect_prop";

  while (i < path.length) {
    const ch = path[i];

    if (state === "expect_prop") {
      if (!/[A-Za-z_]/.test(ch)) return null;
      let j = i + 1;
      while (j < path.length && /[A-Za-z0-9_]/.test(path[j]!)) {
        j += 1;
      }
      tokens.push({ kind: "prop", name: path.slice(i, j) });
      i = j;
      state = "after_prop";
      continue;
    }

    if (state === "after_prop") {
      if (ch === ".") {
        i += 1;
        state = "expect_prop";
        continue;
      }
      if (ch === "[") {
        const parsed = parseIndexAt(path, i);
        if (parsed == null) return null;
        tokens.push({ kind: "index", index: parsed.index });
        i = parsed.next;
        state = "after_index";
        continue;
      }
      return null;
    }

    // state === "after_index"
    if (ch === ".") {
      i += 1;
      state = "expect_prop";
      continue;
    }
    if (ch === "[") {
      const parsed = parseIndexAt(path, i);
      if (parsed == null) return null;
      tokens.push({ kind: "index", index: parsed.index });
      i = parsed.next;
      state = "after_index";
      continue;
    }
    // Property immediately after ] without a dot is malformed.
    return null;
  }

  if (state === "expect_prop") return null;
  return tokens.length > 0 ? tokens : null;
}

function parseIndexAt(
  path: string,
  openBracketIndex: number,
): { index: number; next: number } | null {
  if (path[openBracketIndex] !== "[") return null;
  const close = path.indexOf("]", openBracketIndex + 1);
  if (close < 0) return null;
  const raw = path.slice(openBracketIndex + 1, close);
  if (!/^\d+$/.test(raw)) return null;
  return { index: Number(raw), next: close + 1 };
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
