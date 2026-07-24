import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type {
  ReadStatblockCandidateResponseV1,
  ValidateDefinitionBuddyResponseV1,
} from "../../api/types";
import type {
  GeneratedStatblockCandidateV1,
  ValidationReceiptV1,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import fixture from "../../../../../tests/fixtures/statblocks/v1/candidate-response.json";
import { presentCandidateStatus, StatblockWorkbenchModule } from "./StatblockWorkbenchModule";

const candidate = fixture as GeneratedStatblockCandidateV1;

const activeResponse: ReadStatblockCandidateResponseV1 = {
  schema: "dmb_statblock_candidate_read_v1",
  candidate_id: candidate.candidate_id,
  status: "active",
  candidate,
};

function receipt(
  status: ValidationReceiptV1["status"],
  issues: ValidationReceiptV1["issues"] = [],
): ValidationReceiptV1 {
  return {
    status,
    mode: "editor_preview",
    validator_version: "1",
    canonicalizer_version: "1",
    definition_digest: "sha256:preview-digest",
    issues,
  };
}

function successValidate(
  status: ValidationReceiptV1["status"],
  issues: ValidationReceiptV1["issues"] = [],
): ValidateDefinitionBuddyResponseV1 {
  const validation_receipt = receipt(status, issues);
  return {
    schema: "dmb_statblock_definition_validation_v1",
    outcome: "success",
    definition_digest: validation_receipt.definition_digest,
    validation_receipt,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

async function loadId(id: string) {
  const user = userEvent.setup();
  render(<StatblockWorkbenchModule />);
  await user.type(screen.getByPlaceholderText("cand_…"), id);
  await user.click(screen.getByRole("button", { name: "Load candidate" }));
  return user;
}

describe("presentCandidateStatus", () => {
  it("distinguishes integrity failure from dependency unavailable", () => {
    expect(presentCandidateStatus("unavailable", "integrity_failure").stateKind).toBe(
      "integrity_failure",
    );
    expect(presentCandidateStatus("unavailable", "downstream_unavailable").stateKind).toBe(
      "dependency_unavailable",
    );
    expect(presentCandidateStatus("missing", null).stateKind).toBe("missing");
    expect(presentCandidateStatus("expired", "downstream_expired").stateKind).toBe("expired");
  });
});

describe("StatblockWorkbenchModule", () => {
  it("loads an exact candidate and hosts the editor in edit mode by default", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

    await loadId("cand_fixture1");

    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });
    expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture1");
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("clean_unvalidated");
    expect(screen.getByDisplayValue("Ironhide Brute")).toBeTruthy();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
    expect(screen.queryByText("Preview corpus promotion")).toBeNull();
    expect(screen.queryByRole("button", { name: /accept/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /^save$/i })).toBeNull();
  });

  it("can switch to review source renderer", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

    await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });
    await user.click(screen.getByRole("button", { name: "Review source" }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeTruthy();
    });
    expect(screen.getByText("Greatclub")).toBeTruthy();
  });

  it("shows expired state without mock fallback", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_expired1",
      status: "expired",
      failure_category: "downstream_expired",
      failure_message: "candidate expired",
    });

    await loadId("cand_expired1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate expired" })).toBeTruthy();
    });
    expect(screen.getByText(/cand_expired1/)).toBeTruthy();
    expect(document.querySelector('[data-candidate-status="expired"]')).toBeTruthy();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
  });

  it("shows missing state without mock fallback", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_missing1",
      status: "missing",
    });

    await loadId("cand_missing1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate missing" })).toBeTruthy();
    });
    expect(screen.getByText(/cand_missing1/)).toBeTruthy();
    expect(document.querySelector('[data-candidate-status="missing"]')).toBeTruthy();
    expect(screen.queryByText(/DungeonMindServer outage/i)).toBeNull();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
  });

  it("shows integrity failure distinctly from dependency unavailable", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_integrity1",
      status: "unavailable",
      failure_category: "integrity_failure",
      failure_message: "candidate cache digest mismatch",
    });

    await loadId("cand_integrity1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate integrity failure" })).toBeTruthy();
    });
    expect(screen.getByText(/not a DungeonMindServer outage/i)).toBeTruthy();
    expect(screen.getByText(/cand_integrity1/)).toBeTruthy();
    expect(document.querySelector('[data-candidate-status="integrity_failure"]')).toBeTruthy();
    expect(screen.queryByText("Candidate service unavailable")).toBeNull();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
  });

  it("shows dependency unavailable for non-integrity unavailable categories", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: "cand_down1",
      status: "unavailable",
      failure_category: "downstream_unavailable",
      failure_message: "upstream timeout",
    });

    await loadId("cand_down1");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Candidate service unavailable" })).toBeTruthy();
    });
    expect(document.querySelector('[data-candidate-status="dependency_unavailable"]')).toBeTruthy();
    expect(screen.queryByText(/integrity failure/i)).toBeNull();
    expect(screen.queryByText("Generate mock draft")).toBeNull();
  });

  it("generates from a ThreatDraft then loads the returned candidate", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
      schema: "dmb_generate_threat_draft_candidate_response_v1",
      draft_id: "td_test",
      generated_from_draft_version: 1,
      request_id: "req_1",
      outcome: "success",
      candidate,
      cache_status: "stored",
      persistence_failures: [],
    });
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("td_…"), "td_test");
    await user.click(screen.getByRole("button", { name: "Generate candidate" }));

    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });
    expect(liveApi.generateThreatDraftCandidate).toHaveBeenCalledWith("td_test", {
      expected_draft_version: 1,
    });
    expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture1");
  });

  it("maps clean valid receipt to validated UI status", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });

    const nameInput = screen.getByLabelText("Creature name");
    await user.clear(nameInput);
    await user.type(nameInput, "Validated Name");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("validated");
    });
    expect(screen.getByTestId("editor-ui-status").textContent).not.toContain(
      "validated_with_warnings",
    );
    expect(document.querySelector('[data-preview-state="current"]')).toBeTruthy();
    expect(document.querySelector('[data-preview-receipt-status="valid"]')).toBeTruthy();
    expect(liveApi.validateStatblockDefinition).toHaveBeenCalled();
    const call = vi.mocked(liveApi.validateStatblockDefinition).mock.calls[0][0];
    expect(call.definition.identity.name).toBe("Validated Name");
  });

  it("demonstrates edit → validate → edit → stale", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(
      successValidate("warnings", [
        {
          code: "BALANCE_WARNING",
          severity: "warning",
          field_path: "identity.name",
          message: "name looks odd",
        },
      ]),
    );

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });

    const nameInput = screen.getByLabelText("Creature name");
    await user.clear(nameInput);
    await user.type(nameInput, "Once");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain(
        "validated_with_warnings",
      );
    });
    expect(document.querySelector('[data-preview-state="current"]')).toBeTruthy();

    await user.clear(nameInput);
    await user.type(nameInput, "Twice");

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
    });
    expect(document.querySelector('[data-preview-state="stale"]')).toBeTruthy();
    expect(screen.getByText(/stale \/ not current/i)).toBeTruthy();
  });

  it("discards stale validate responses after an intervening edit", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    let resolveValidate: (value: ValidateDefinitionBuddyResponseV1) => void = () => undefined;
    vi.spyOn(liveApi, "validateStatblockDefinition").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveValidate = resolve;
        }),
    );

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });

    const nameInput = screen.getByLabelText("Creature name");
    await user.clear(nameInput);
    await user.type(nameInput, "Before Validate");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("validating");
    });

    await user.clear(nameInput);
    await user.type(nameInput, "Edited During Flight");

    resolveValidate(successValidate("valid"));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
    });
    expect(screen.getByTestId("editor-ui-status").textContent).not.toContain("Status: validated");
    expect(document.querySelector('[data-preview-state="current"]')).toBeNull();
    expect(screen.getByDisplayValue("Edited During Flight")).toBeTruthy();
  });

  it("preserves edits when validation dependency fails", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue({
      schema: "dmb_statblock_definition_validation_v1",
      outcome: "failure",
      failure_category: "downstream_timeout",
      failure_message: "upstream timed out",
    });

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });

    const nameInput = screen.getByLabelText("Creature name");
    await user.clear(nameInput);
    await user.type(nameInput, "Kept On Timeout");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("validation_unavailable");
    });
    expect(screen.getByDisplayValue("Kept On Timeout")).toBeTruthy();
    expect(document.querySelector('[data-preview-state="unavailable"]')).toBeTruthy();
    expect(screen.queryByRole("button", { name: /accept/i })).toBeNull();
  });

  it("shows field and global issues distinctly for invalid receipts", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(
      successValidate("invalid", [
        {
          code: "MISSING_ATTACK_BONUS",
          severity: "error",
          field_path: "rule_elements[0].mechanic",
          message: "missing attack bonus",
        },
        {
          code: "MALFORMED",
          severity: "warning",
          field_path: "",
          message: "malformed path issue",
        },
      ]),
    );

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: "Validate working copy" }));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("validated_with_errors");
    });

    const fieldPanel = screen.getByTestId("preview-field-issues");
    const globalPanel = screen.getByTestId("preview-global-issues");
    expect(fieldPanel.textContent).toMatch(/missing attack bonus/);
    expect(fieldPanel.querySelector('[data-issue-severity="error"]')).toBeTruthy();
    expect(globalPanel.textContent).toMatch(/malformed path issue/);
    expect(globalPanel.querySelector('[data-issue-severity="warning"]')).toBeTruthy();
  });
});
