import { describe, expect, it } from "vitest";

import type { ValidationIssueV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import {
  mapServerValidationStatus,
  partitionValidationIssuesByPath,
  splitIssuesBySeverity,
} from "./statblockValidationIssues";

function issue(
  overrides: Partial<ValidationIssueV1> & Pick<ValidationIssueV1, "code" | "severity" | "field_path" | "message">,
): ValidationIssueV1 {
  return overrides;
}

describe("statblockValidationIssues", () => {
  it("maps pathable issues to field and empty/malformed paths to global", () => {
    const issues = [
      issue({
        code: "MISSING_ATTACK_BONUS",
        severity: "error",
        field_path: "rule_elements[0].mechanic",
        message: "missing bonus",
      }),
      issue({
        code: "BALANCE_WARNING",
        severity: "warning",
        field_path: "   ",
        message: "whitespace path",
      }),
      issue({
        code: "UNKNOWN",
        severity: "error",
        field_path: "",
        message: "empty path",
      }),
    ];

    const partitioned = partitionValidationIssuesByPath(issues);
    expect(partitioned.fieldIssues).toHaveLength(1);
    expect(partitioned.fieldIssues[0].code).toBe("MISSING_ATTACK_BONUS");
    expect(partitioned.globalIssues).toHaveLength(2);
    expect(partitioned.globalIssues.map((entry) => entry.code)).toEqual([
      "BALANCE_WARNING",
      "UNKNOWN",
    ]);
  });

  it("keeps errors and warnings distinct by severity", () => {
    const issues = [
      issue({
        code: "E1",
        severity: "error",
        field_path: "identity.name",
        message: "err",
      }),
      issue({
        code: "W1",
        severity: "warning",
        field_path: "identity.name",
        message: "warn",
      }),
      issue({
        code: "I1",
        severity: "info",
        field_path: "identity.name",
        message: "info",
      }),
    ];
    const { errors, warnings } = splitIssuesBySeverity(issues);
    expect(errors.map((entry) => entry.code)).toEqual(["E1"]);
    expect(warnings.map((entry) => entry.code)).toEqual(["W1", "I1"]);
  });

  it("maps Server validation statuses onto receipt-bearing UI statuses", () => {
    expect(mapServerValidationStatus("valid")).toBe("validated");
    expect(mapServerValidationStatus("warnings")).toBe("validated_with_warnings");
    expect(mapServerValidationStatus("invalid")).toBe("validated_with_errors");
  });
});
