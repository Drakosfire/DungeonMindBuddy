import { describe, expect, it } from "vitest";

import type { ValidationIssueV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { baseCandidateDefinition } from "./editorFixtures";
import { definitionOutputToInput } from "./definitionOutputToInput";
import {
  mapServerValidationStatus,
  parseFieldPath,
  partitionValidationIssuesByPath,
  resolveFieldPathAgainstWorkingCopy,
  splitIssuesBySeverity,
} from "./statblockValidationIssues";

function issue(
  overrides: Partial<ValidationIssueV1> &
    Pick<ValidationIssueV1, "code" | "severity" | "field_path" | "message">,
): ValidationIssueV1 {
  return overrides;
}

const workingCopy = definitionOutputToInput(baseCandidateDefinition());

describe("statblockValidationIssues", () => {
  it("parses exact path syntax and rejects malformed forms", () => {
    expect(parseFieldPath("identity.name")).toEqual([
      { kind: "prop", name: "identity" },
      { kind: "prop", name: "name" },
    ]);
    expect(parseFieldPath("rule_elements[0].mechanic")).toEqual([
      { kind: "prop", name: "rule_elements" },
      { kind: "index", index: 0 },
      { kind: "prop", name: "mechanic" },
    ]);
    expect(parseFieldPath("identity..name")).toBeNull();
    expect(parseFieldPath(".identity.name")).toBeNull();
    expect(parseFieldPath("identity.name.")).toBeNull();
    expect(parseFieldPath("rule_elements[abc].mechanic")).toBeNull();
    expect(parseFieldPath("")).toBeNull();
    expect(parseFieldPath("   ")).toBeNull();
  });

  it("resolves only paths that exist on the current working copy", () => {
    const identityName = parseFieldPath("identity.name");
    expect(identityName).not.toBeNull();
    expect(resolveFieldPathAgainstWorkingCopy(workingCopy, identityName!)).toBe(true);

    const outOfRange = parseFieldPath("rule_elements[999].mechanic");
    expect(outOfRange).not.toBeNull();
    expect(resolveFieldPathAgainstWorkingCopy(workingCopy, outOfRange!)).toBe(false);

    const future = parseFieldPath("future_contract.new_region");
    expect(future).not.toBeNull();
    expect(resolveFieldPathAgainstWorkingCopy(workingCopy, future!)).toBe(false);
  });

  it("maps resolvable paths to field and malformed/unmappable paths to global", () => {
    const issues = [
      issue({
        code: "MISSING_ATTACK_BONUS",
        severity: "error",
        field_path: "rule_elements[0].mechanic",
        message: "missing bonus",
      }),
      issue({
        code: "MALFORMED_DOTS",
        severity: "warning",
        field_path: "identity..name",
        message: "malformed dots",
      }),
      issue({
        code: "LEADING_DOT",
        severity: "error",
        field_path: ".identity.name",
        message: "leading dot",
      }),
      issue({
        code: "BAD_INDEX",
        severity: "warning",
        field_path: "rule_elements[abc].mechanic",
        message: "bad index",
      }),
      issue({
        code: "OOR",
        severity: "error",
        field_path: "rule_elements[999].mechanic",
        message: "out of range",
      }),
      issue({
        code: "FUTURE",
        severity: "info",
        field_path: "future_contract.new_region",
        message: "future path",
      }),
      issue({
        code: "EMPTY",
        severity: "warning",
        field_path: "",
        message: "empty path",
      }),
    ];

    const partitioned = partitionValidationIssuesByPath(issues, workingCopy);
    expect(partitioned.fieldIssues.map((entry) => entry.code)).toEqual(["MISSING_ATTACK_BONUS"]);
    expect(partitioned.globalIssues.map((entry) => entry.code)).toEqual([
      "MALFORMED_DOTS",
      "LEADING_DOT",
      "BAD_INDEX",
      "OOR",
      "FUTURE",
      "EMPTY",
    ]);
    // Original non-empty paths remain on global issues for visible disclosure.
    expect(partitioned.globalIssues.find((entry) => entry.code === "FUTURE")?.field_path).toBe(
      "future_contract.new_region",
    );
  });

  it("preserves info, warning, and error severities exactly", () => {
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
    const { errors, warnings, infos } = splitIssuesBySeverity(issues);
    expect(errors.map((entry) => entry.code)).toEqual(["E1"]);
    expect(warnings.map((entry) => entry.code)).toEqual(["W1"]);
    expect(infos.map((entry) => entry.code)).toEqual(["I1"]);
  });

  it("keeps informational issues in field and global partitions without relabeling", () => {
    const issues = [
      issue({
        code: "INFO_FIELD",
        severity: "info",
        field_path: "abilities.strength",
        message: "field info",
      }),
      issue({
        code: "INFO_GLOBAL",
        severity: "info",
        field_path: "",
        message: "global info",
      }),
    ];
    const { fieldIssues, globalIssues } = partitionValidationIssuesByPath(issues, workingCopy);
    expect(splitIssuesBySeverity(fieldIssues).infos.map((entry) => entry.code)).toEqual([
      "INFO_FIELD",
    ]);
    expect(splitIssuesBySeverity(globalIssues).infos.map((entry) => entry.code)).toEqual([
      "INFO_GLOBAL",
    ]);
    expect(splitIssuesBySeverity(fieldIssues).warnings).toHaveLength(0);
    expect(splitIssuesBySeverity(globalIssues).warnings).toHaveLength(0);
  });

  it("maps Server validation statuses onto receipt-bearing UI statuses", () => {
    expect(mapServerValidationStatus("valid")).toBe("validated");
    expect(mapServerValidationStatus("warnings")).toBe("validated_with_warnings");
    expect(mapServerValidationStatus("invalid")).toBe("validated_with_errors");
  });
});
