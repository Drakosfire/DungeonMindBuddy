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

/** Non-empty field_path maps to field; empty/whitespace → global (never dropped). */
export function partitionValidationIssuesByPath(
  issues: ValidationIssueV1[] | null | undefined,
): PartitionedValidationIssues {
  const fieldIssues: ValidationIssueV1[] = [];
  const globalIssues: ValidationIssueV1[] = [];
  for (const issue of issues ?? []) {
    if (typeof issue.field_path === "string" && issue.field_path.trim().length > 0) {
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
