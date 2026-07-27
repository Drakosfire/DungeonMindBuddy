import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type {
  AcceptThreatDraftMechanicsResponseV1,
  ReadStatblockCandidateResponseV1,
  GenerateThreatDraftCandidateResponseV1,
  ValidateDefinitionBuddyResponseV1,
} from "../../api/types";
import type {
  GeneratedStatblockCandidateV1,
  ValidationReceiptV1,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import fixture from "../../../../../tests/fixtures/statblocks/v1/candidate-response.json";
import {
  ACCEPT_RESTORE_LOOKUP,
  presentCandidateStatus,
  StatblockWorkbenchModule,
} from "./StatblockWorkbenchModule";

const candidate = fixture as GeneratedStatblockCandidateV1;

const activeResponse: ReadStatblockCandidateResponseV1 = {
  schema: "dmb_statblock_candidate_read_v1",
  candidate_id: candidate.candidate_id,
  status: "active",
  candidate,
};

const PREVIEW_DIGEST = `sha256:${"a".repeat(64)}`;

function receipt(
  status: ValidationReceiptV1["status"],
  issues: ValidationReceiptV1["issues"] = [],
): ValidationReceiptV1 {
  return {
    status,
    mode: "editor_preview",
    validator_version: "1",
    canonicalizer_version: "1",
    definition_digest: PREVIEW_DIGEST,
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
  sessionStorage.clear();
  ACCEPT_RESTORE_LOOKUP.delayMs = 40;
  ACCEPT_RESTORE_LOOKUP.maxAttempts = 3;
});

async function loadId(id: string) {
  const user = userEvent.setup();
  render(<StatblockWorkbenchModule />);
  await user.type(screen.getByPlaceholderText("cand_…"), id);
  await user.click(screen.getByRole("button", { name: "Load candidate" }));
  return user;
}

async function validateWorkingCopy(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Validate working copy" }));
  await waitFor(() => {
    expect(document.querySelector('[data-preview-state="current"]')).toBeTruthy();
  });
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
    expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
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
    // Bottom tools stay available while reviewing the rendered source.
    expect(screen.getByTestId("workbench-edit-dock")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Validate working copy" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeTruthy();
    expect(screen.queryByTestId("statblock-definition-editor")).toBeNull();
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

  it("ignores late generation success after a newer manual load", async () => {
    const candidateB: GeneratedStatblockCandidateV1 = {
      ...candidate,
      candidate_id: "cand_fixture2",
      definition: {
        ...candidate.definition,
        identity: {
          ...candidate.definition.identity,
          name: "Manual Selection",
        },
      },
    };
    const activeB: ReadStatblockCandidateResponseV1 = {
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: candidateB.candidate_id,
      status: "active",
      candidate: candidateB,
    };

    let resolveGenerate: (value: GenerateThreatDraftCandidateResponseV1) => void = () => {};
    vi.spyOn(liveApi, "generateThreatDraftCandidate").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveGenerate = resolve;
        }),
    );
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeB);

    const user = userEvent.setup();
    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("td_…"), "td_stale");
    await user.click(screen.getByRole("button", { name: "Generate candidate" }));
    await waitFor(() => {
      expect(liveApi.generateThreatDraftCandidate).toHaveBeenCalled();
    });

    await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture2");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(screen.getByDisplayValue("Manual Selection")).toBeTruthy();
    });
    expect(screen.getByPlaceholderText("cand_…")).toHaveProperty("value", "cand_fixture2");

    resolveGenerate({
      schema: "dmb_generate_threat_draft_candidate_response_v1",
      draft_id: "td_stale",
      generated_from_draft_version: 1,
      request_id: "req_stale",
      outcome: "success",
      candidate,
      cache_status: "stored",
      persistence_failures: [],
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Manual Selection")).toBeTruthy();
    });
    expect(screen.queryByDisplayValue("Ironhide Brute")).toBeNull();
    expect(screen.getByPlaceholderText("cand_…")).toHaveProperty("value", "cand_fixture2");
    expect(screen.queryByText(/Generated cand_fixture1/i)).toBeNull();
    expect(liveApi.getStatblockCandidate).toHaveBeenCalledTimes(1);
    expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture2");
  });

  it("ignores late generation failure after a newer manual load", async () => {
    const candidateB: GeneratedStatblockCandidateV1 = {
      ...candidate,
      candidate_id: "cand_fixture2",
      definition: {
        ...candidate.definition,
        identity: {
          ...candidate.definition.identity,
          name: "Manual Selection",
        },
      },
    };
    const activeB: ReadStatblockCandidateResponseV1 = {
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: candidateB.candidate_id,
      status: "active",
      candidate: candidateB,
    };

    let rejectGenerate: (reason?: unknown) => void = () => {};
    vi.spyOn(liveApi, "generateThreatDraftCandidate").mockImplementation(
      () =>
        new Promise((_, reject) => {
          rejectGenerate = reject;
        }),
    );
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeB);

    const user = userEvent.setup();
    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("td_…"), "td_fail");
    await user.click(screen.getByRole("button", { name: "Generate candidate" }));
    await waitFor(() => {
      expect(liveApi.generateThreatDraftCandidate).toHaveBeenCalled();
    });

    await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture2");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(screen.getByDisplayValue("Manual Selection")).toBeTruthy();
    });

    rejectGenerate(new Error("stale generation boom"));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Manual Selection")).toBeTruthy();
    });
    expect(screen.queryByText(/stale generation boom/i)).toBeNull();
    expect(screen.queryByText(/Unable to generate candidate/i)).toBeNull();
  });

  it("lets a newer generation win over a late prior manual load", async () => {
    const candidateB: GeneratedStatblockCandidateV1 = {
      ...candidate,
      candidate_id: "cand_fixture2",
      definition: {
        ...candidate.definition,
        identity: {
          ...candidate.definition.identity,
          name: "Generated Winner",
        },
      },
    };
    const activeB: ReadStatblockCandidateResponseV1 = {
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: candidateB.candidate_id,
      status: "active",
      candidate: candidateB,
    };

    let resolveLoadA: (value: ReadStatblockCandidateResponseV1) => void = () => {};
    vi.spyOn(liveApi, "getStatblockCandidate").mockImplementation((id: string) => {
      if (id === "cand_fixture1") {
        return new Promise((resolve) => {
          resolveLoadA = resolve;
        });
      }
      return Promise.resolve(activeB);
    });
    vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
      schema: "dmb_generate_threat_draft_candidate_response_v1",
      draft_id: "td_win",
      generated_from_draft_version: 1,
      request_id: "req_win",
      outcome: "success",
      candidate: candidateB,
      cache_status: "stored",
      persistence_failures: [],
    });

    const user = userEvent.setup();
    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture1");
    });

    await user.type(screen.getByPlaceholderText("td_…"), "td_win");
    await user.click(screen.getByRole("button", { name: "Generate candidate" }));
    await waitFor(() => {
      expect(screen.getByDisplayValue("Generated Winner")).toBeTruthy();
    });

    resolveLoadA(activeResponse);
    await waitFor(() => {
      expect(screen.getByDisplayValue("Generated Winner")).toBeTruthy();
    });
    expect(screen.queryByDisplayValue("Ironhide Brute")).toBeNull();
    expect(screen.getByPlaceholderText("cand_…")).toHaveProperty("value", "cand_fixture2");
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

    // Immediate invalidation — do not wait for the old promise.
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
    expect(screen.getByRole("button", { name: "Validate working copy" })).not.toBeDisabled();

    resolveValidate(successValidate("valid"));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
    });
    expect(screen.getByTestId("editor-ui-status").textContent).not.toContain("Status: validated");
    expect(document.querySelector('[data-preview-state="current"]')).toBeNull();
    expect(screen.getByDisplayValue("Edited During Flight")).toBeTruthy();
  });

  it("allows a newer validate to win when an older request resolves later", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    const resolvers: Array<(value: ValidateDefinitionBuddyResponseV1) => void> = [];
    const rejectors: Array<(reason?: unknown) => void> = [];
    vi.spyOn(liveApi, "validateStatblockDefinition").mockImplementation(
      () =>
        new Promise((resolve, reject) => {
          resolvers.push(resolve);
          rejectors.push(reject);
        }),
    );

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });

    const nameInput = screen.getByLabelText("Creature name");
    await user.clear(nameInput);
    await user.type(nameInput, "First");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));
    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("validating");
    });
    expect(resolvers).toHaveLength(1);

    await user.clear(nameInput);
    await user.type(nameInput, "Second");
    expect(screen.getByRole("button", { name: "Validate working copy" })).not.toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Validate working copy" }));
    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("validating");
    });
    expect(resolvers).toHaveLength(2);

    resolvers[1](successValidate("valid"));
    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toMatch(/Status: validated$/);
    });

    // Old request settles later — must not disturb the newer association.
    resolvers[0](successValidate("invalid"));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toMatch(/Status: validated$/);
    });
    expect(document.querySelector('[data-preview-receipt-status="valid"]')).toBeTruthy();
    expect(document.querySelector('[data-preview-state="unavailable"]')).toBeNull();
  });

  it("ignores a late reject from an older validate after a newer validate succeeds", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    const resolvers: Array<(value: ValidateDefinitionBuddyResponseV1) => void> = [];
    const rejectors: Array<(reason?: unknown) => void> = [];
    vi.spyOn(liveApi, "validateStatblockDefinition").mockImplementation(
      () =>
        new Promise((resolve, reject) => {
          resolvers.push(resolve);
          rejectors.push(reject);
        }),
    );

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });

    const nameInput = screen.getByLabelText("Creature name");
    await user.clear(nameInput);
    await user.type(nameInput, "First");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));
    await waitFor(() => {
      expect(resolvers).toHaveLength(1);
    });

    await user.clear(nameInput);
    await user.type(nameInput, "Second");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));
    await waitFor(() => {
      expect(resolvers).toHaveLength(2);
    });

    resolvers[1](successValidate("warnings"));
    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain(
        "validated_with_warnings",
      );
    });

    rejectors[0](new Error("late reject should be ignored"));
    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain(
        "validated_with_warnings",
      );
    });
    expect(document.querySelector('[data-preview-state="unavailable"]')).toBeNull();
  });

  it("does not apply unavailable UI from a stale rejected validate after edit", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    let rejectValidate: (reason?: unknown) => void = () => undefined;
    vi.spyOn(liveApi, "validateStatblockDefinition").mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          rejectValidate = reject;
        }),
    );

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });

    const nameInput = screen.getByLabelText("Creature name");
    await user.clear(nameInput);
    await user.type(nameInput, "Before Reject");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("validating");
    });

    await user.clear(nameInput);
    await user.type(nameInput, "Edited Before Reject");
    expect(screen.getByRole("button", { name: "Validate working copy" })).not.toBeDisabled();
    rejectValidate(new Error("upstream timed out"));

    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
    });
    expect(screen.getByTestId("editor-ui-status").textContent).not.toContain(
      "validation_unavailable",
    );
    expect(document.querySelector('[data-preview-state="unavailable"]')).toBeNull();
    expect(screen.queryByText(/Validation unavailable/i)).toBeNull();
    expect(screen.getByDisplayValue("Edited Before Reject")).toBeTruthy();
  });

  it("clears revision-owned failure UI immediately on later edit", async () => {
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
    await user.type(nameInput, "Will Fail");
    await user.click(screen.getByRole("button", { name: "Validate working copy" }));

    await waitFor(() => {
      expect(document.querySelector('[data-preview-state="unavailable"]')).toBeTruthy();
    });

    await user.clear(nameInput);
    await user.type(nameInput, "After Failure");
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
    expect(document.querySelector('[data-preview-state="unavailable"]')).toBeNull();
    expect(screen.queryByText(/Validation unavailable/i)).toBeNull();
  });

  it("invalidates in-flight validation when loading another candidate", async () => {
    const candidateB: GeneratedStatblockCandidateV1 = {
      ...candidate,
      candidate_id: "cand_fixture2",
      definition: {
        ...candidate.definition,
        identity: {
          ...candidate.definition.identity,
          name: "Second Candidate",
        },
      },
    };
    const activeB: ReadStatblockCandidateResponseV1 = {
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: candidateB.candidate_id,
      status: "active",
      candidate: candidateB,
    };

    vi.spyOn(liveApi, "getStatblockCandidate").mockImplementation(async (id: string) => {
      if (id === "cand_fixture2") return activeB;
      return activeResponse;
    });

    let resolveValidate: (value: ValidateDefinitionBuddyResponseV1) => void = () => undefined;
    vi.spyOn(liveApi, "validateStatblockDefinition").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveValidate = resolve;
        }),
    );

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByDisplayValue("Ironhide Brute")).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: "Validate working copy" }));
    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toContain("validating");
    });

    const candidateInput = screen.getByPlaceholderText("cand_…");
    await user.clear(candidateInput);
    await user.type(candidateInput, "cand_fixture2");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Second Candidate")).toBeTruthy();
    });
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("clean_unvalidated");
    expect(screen.getByRole("button", { name: "Validate working copy" })).not.toBeDisabled();

    resolveValidate(successValidate("valid"));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Second Candidate")).toBeTruthy();
    });
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("clean_unvalidated");
    expect(screen.getByTestId("editor-ui-status").textContent).not.toContain("Status: validated");
    expect(document.querySelector('[data-preview-state="current"]')).toBeNull();
  });

  it("keeps newer candidate when an older load resolves later", async () => {
    const candidateB: GeneratedStatblockCandidateV1 = {
      ...candidate,
      candidate_id: "cand_fixture2",
      definition: {
        ...candidate.definition,
        identity: {
          ...candidate.definition.identity,
          name: "Second Candidate",
        },
      },
    };
    const activeB: ReadStatblockCandidateResponseV1 = {
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: candidateB.candidate_id,
      status: "active",
      candidate: candidateB,
    };

    const loadResolvers = new Map<string, (value: ReadStatblockCandidateResponseV1) => void>();
    vi.spyOn(liveApi, "getStatblockCandidate").mockImplementation(
      (id: string) =>
        new Promise((resolve) => {
          loadResolvers.set(id, resolve);
        }),
    );

    const user = userEvent.setup();
    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(loadResolvers.has("cand_fixture1")).toBe(true);
    });

    const candidateInput = screen.getByPlaceholderText("cand_…");
    await user.clear(candidateInput);
    await user.type(candidateInput, "cand_fixture2");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(loadResolvers.has("cand_fixture2")).toBe(true);
    });

    loadResolvers.get("cand_fixture2")!(activeB);
    await waitFor(() => {
      expect(screen.getByDisplayValue("Second Candidate")).toBeTruthy();
    });

    loadResolvers.get("cand_fixture1")!(activeResponse);
    await waitFor(() => {
      expect(screen.getByDisplayValue("Second Candidate")).toBeTruthy();
    });
    expect(screen.queryByDisplayValue("Ironhide Brute")).toBeNull();
  });

  it("ignores stale load errors after a newer candidate is active", async () => {
    const candidateB: GeneratedStatblockCandidateV1 = {
      ...candidate,
      candidate_id: "cand_fixture2",
      definition: {
        ...candidate.definition,
        identity: {
          ...candidate.definition.identity,
          name: "Second Candidate",
        },
      },
    };
    const activeB: ReadStatblockCandidateResponseV1 = {
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: candidateB.candidate_id,
      status: "active",
      candidate: candidateB,
    };

    const loadResolvers = new Map<
      string,
      {
        resolve: (value: ReadStatblockCandidateResponseV1) => void;
        reject: (reason?: unknown) => void;
      }
    >();
    vi.spyOn(liveApi, "getStatblockCandidate").mockImplementation(
      (id: string) =>
        new Promise((resolve, reject) => {
          loadResolvers.set(id, { resolve, reject });
        }),
    );

    const user = userEvent.setup();
    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(loadResolvers.has("cand_fixture1")).toBe(true);
    });

    const candidateInput = screen.getByPlaceholderText("cand_…");
    await user.clear(candidateInput);
    await user.type(candidateInput, "cand_fixture2");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(loadResolvers.has("cand_fixture2")).toBe(true);
    });

    loadResolvers.get("cand_fixture2")!.resolve(activeB);
    await waitFor(() => {
      expect(screen.getByDisplayValue("Second Candidate")).toBeTruthy();
    });

    loadResolvers.get("cand_fixture1")!.reject(new Error("stale A failed"));
    await waitFor(() => {
      expect(screen.getByDisplayValue("Second Candidate")).toBeTruthy();
    });
    expect(screen.queryByText(/stale A failed/i)).toBeNull();
  });

  it("does not let a stale load steal a newer candidate validate receipt", async () => {
    const candidateB: GeneratedStatblockCandidateV1 = {
      ...candidate,
      candidate_id: "cand_fixture2",
      definition: {
        ...candidate.definition,
        identity: {
          ...candidate.definition.identity,
          name: "Second Candidate",
        },
      },
    };
    const activeB: ReadStatblockCandidateResponseV1 = {
      schema: "dmb_statblock_candidate_read_v1",
      candidate_id: candidateB.candidate_id,
      status: "active",
      candidate: candidateB,
    };

    const loadResolvers = new Map<string, (value: ReadStatblockCandidateResponseV1) => void>();
    vi.spyOn(liveApi, "getStatblockCandidate").mockImplementation(
      (id: string) =>
        new Promise((resolve) => {
          loadResolvers.set(id, resolve);
        }),
    );
    vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));

    const user = userEvent.setup();
    render(<StatblockWorkbenchModule />);
    await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture1");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(loadResolvers.has("cand_fixture1")).toBe(true);
    });

    const candidateInput = screen.getByPlaceholderText("cand_…");
    await user.clear(candidateInput);
    await user.type(candidateInput, "cand_fixture2");
    await user.click(screen.getByRole("button", { name: "Load candidate" }));
    await waitFor(() => {
      expect(loadResolvers.has("cand_fixture2")).toBe(true);
    });

    loadResolvers.get("cand_fixture2")!(activeB);
    await waitFor(() => {
      expect(screen.getByDisplayValue("Second Candidate")).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: "Validate working copy" }));
    await waitFor(() => {
      expect(screen.getByTestId("editor-ui-status").textContent).toMatch(/Status: validated$/);
    });

    loadResolvers.get("cand_fixture1")!(activeResponse);
    await waitFor(() => {
      expect(screen.getByDisplayValue("Second Candidate")).toBeTruthy();
    });
    expect(screen.queryByDisplayValue("Ironhide Brute")).toBeNull();
    expect(screen.getByTestId("editor-ui-status").textContent).toMatch(/Status: validated$/);
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
    expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
    const dock = screen.getByTestId("workbench-edit-dock");
    expect(dock.textContent).toMatch(/Validate failed:.*upstream timed out/i);
    expect(dock.querySelector('[data-dock-tone="error"]')).toBeTruthy();
  });

  it("surfaces Accept transport failures in the edit dock", async () => {
    vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
    vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
    vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockRejectedValue(
      new Error(
        "API response is not valid JSON (HTTP 500). The API returned an HTML page instead of JSON. Usually the L3 server is not running, or the UI is not proxying /api to it.",
      ),
    );

    const user = await loadId("cand_fixture1");
    await waitFor(() => {
      expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
    });
    await user.type(screen.getByPlaceholderText("td_…"), "td_dock_err");
    await validateWorkingCopy(user);
    await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

    await waitFor(() => {
      const dock = screen.getByTestId("workbench-edit-dock");
      expect(dock.textContent).toMatch(
        /Accept failed: HTTP 500 returned HTML instead of JSON/i,
      );
      expect(dock.querySelector('[data-dock-tone="error"][role="alert"]')).toBeTruthy();
    });
  });

  it("shows resolvable field issues and sends malformed/unmappable paths to global", async () => {
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
          code: "BALANCE_WARNING",
          severity: "warning",
          field_path: "identity.name",
          message: "name warning",
        },
        {
          code: "STYLE_INFO",
          severity: "info",
          field_path: "abilities.strength",
          message: "field informational note",
        },
        {
          code: "MALFORMED",
          severity: "warning",
          field_path: "identity..name",
          message: "malformed path issue",
          suggested_resolution: "Fix the path separators",
        },
        {
          code: "MISSING_DOT",
          severity: "error",
          field_path: "rule_elements[0]mechanic",
          message: "missing dot after index",
          suggested_resolution: "Insert a dot after the closing bracket",
        },
        {
          code: "FUTURE",
          severity: "info",
          field_path: "future_contract.new_region",
          message: "future path note",
          suggested_resolution: null,
        },
        {
          code: "GLOBAL_INFO",
          severity: "info",
          field_path: "",
          message: "global informational note",
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
    expect(fieldPanel.textContent).toMatch(/name warning/);
    expect(fieldPanel.querySelector('[data-issue-severity="warning"]')).toBeTruthy();
    expect(fieldPanel.textContent).toMatch(/field informational note/);
    expect(fieldPanel.querySelector('[data-issue-severity="info"]')?.textContent).toMatch(
      /\[info\].*field informational note/,
    );
    expect(fieldPanel.textContent).not.toMatch(/malformed path issue/);
    expect(fieldPanel.textContent).not.toMatch(/future path note/);
    expect(fieldPanel.textContent).not.toMatch(/missing dot after index/);

    expect(globalPanel.querySelector('[data-issue-code="MALFORMED"]')).toBeTruthy();
    expect(globalPanel.querySelector('[data-issue-severity-label="warning"]')).toBeTruthy();
    expect(globalPanel.querySelector('[data-issue-path="identity..name"]')).toBeTruthy();
    expect(globalPanel.querySelector('[data-issue-message="malformed path issue"]')).toBeTruthy();
    expect(
      globalPanel.querySelector('[data-issue-suggested-resolution="Fix the path separators"]'),
    ).toBeTruthy();

    expect(globalPanel.querySelector('[data-issue-code="MISSING_DOT"]')).toBeTruthy();
    expect(globalPanel.querySelector('[data-issue-path="rule_elements[0]mechanic"]')).toBeTruthy();
    expect(
      globalPanel.querySelector(
        '[data-issue-suggested-resolution="Insert a dot after the closing bracket"]',
      ),
    ).toBeTruthy();

    expect(globalPanel.querySelector('[data-issue-code="FUTURE"]')).toBeTruthy();
    expect(
      globalPanel.querySelector('[data-issue-path="future_contract.new_region"]'),
    ).toBeTruthy();
    expect(globalPanel.querySelector('[data-issue-message="future path note"]')).toBeTruthy();

    expect(globalPanel.textContent).toMatch(/global informational note/);
    expect(globalPanel.querySelector('[data-issue-severity="info"]')).toBeTruthy();
    expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
  });

  describe("accept/save mechanics (SBW07c)", () => {
    beforeEach(() => {
      ACCEPT_RESTORE_LOOKUP.delayMs = 0;
      ACCEPT_RESTORE_LOOKUP.maxAttempts = 3;
    });

    it("shows Accept/Save after valid preview and accepts with a single in-flight operation_id", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      let resolveAccept!: (value: AcceptThreatDraftMechanicsResponseV1) => void;
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveAccept = resolve;
          }),
      );
      vi.spyOn(crypto, "randomUUID").mockReturnValue("11111111-2222-4333-8444-555555555555");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await user.type(screen.getByPlaceholderText("td_…"), "td_accept1");
      await validateWorkingCopy(user);

      const acceptButton = screen.getByRole("button", { name: "Accept/Save mechanics" });
      expect(acceptButton).toBeTruthy();
      expect(screen.getByTestId("workbench-edit-dock").textContent).toMatch(
        /not World Graph publish/i,
      );

      await user.click(acceptButton);
      // Concurrent Accept/Save clicks are disabled / guarded — second click must not start another request.
      await waitFor(() => {
        expect(acceptButton).toBeDisabled();
      });
      await user.click(acceptButton);

      await waitFor(() => {
        expect(acceptSpy).toHaveBeenCalledTimes(1);
      });
      expect(acceptSpy.mock.calls[0][1].operation_id).toBe(
        "11111111-2222-4333-8444-555555555555",
      );
      expect(acceptSpy.mock.calls[0][0]).toBe("td_accept1");
      expect(acceptSpy.mock.calls[0][1].expected_draft_version).toBe(1);
      expect(acceptSpy.mock.calls[0][1].validation_definition_digest).toBe(PREVIEW_DIGEST);
      expect(acceptSpy.mock.calls[0][1].source_candidate_id).toBe("cand_fixture1");

      resolveAccept({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_accept1",
        operation_id: "11111111-2222-4333-8444-555555555555",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_1",
          revision_id: "rev_1",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });
      await waitFor(() => {
        expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_accept1")).toBe(
        "11111111-2222-4333-8444-555555555555",
      );
    });

    it("shows mechanics_saved locator and not-published wording", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_saved",
        operation_id: "op_saved",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_1",
          revision_id: "rev_1",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await user.type(screen.getByPlaceholderText("td_…"), "td_saved");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

      await waitFor(() => {
        expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
      });
      expect(screen.getByText(/sb_1/)).toBeTruthy();
      expect(screen.getByText(/rev_1/)).toBeTruthy();
      expect(screen.queryByText("Preview corpus promotion")).toBeNull();
    });

    it("offers reconcile when reference is pending", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("warnings"));
      vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_pending",
        operation_id: "op_pending",
        result_label: "server_committed_reference_pending",
        authority_state: "server_committed",
      });
      const reconcileSpy = vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_pending",
        operation_id: "op_pending",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_reconciled",
          revision_id: "rev_reconciled",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_pending");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await user.type(screen.getByPlaceholderText("td_…"), "td_pending");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Reconcile acceptance" })).toBeTruthy();
      });
      const pendingPanel = screen.getByTestId("accept-mechanics-flow");
      expect(pendingPanel.textContent).toMatch(/ThreatDraft attachment is still pending/i);
      expect(pendingPanel.textContent).not.toMatch(/Mechanics saved/i);
      await user.click(screen.getByRole("button", { name: "Reconcile acceptance" }));

      await waitFor(() => {
        expect(reconcileSpy).toHaveBeenCalledWith("td_pending", "op_pending");
      });
      expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
    });

    it("does not offer reconcile for accepted_ref_conflict even when authority is server_committed", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_conflict",
        operation_id: "op_conflict",
        result_label: "accepted_ref_conflict",
        authority_state: "server_committed",
        draft_ref: "conflicted",
        message: "draft already has different accepted mechanics",
      });
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_conflict");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await user.type(screen.getByPlaceholderText("td_…"), "td_conflict");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

      await waitFor(() => {
        expect(screen.getByTestId("accept-ref-conflict")).toBeTruthy();
      });
      expect(screen.queryByRole("button", { name: "Reconcile acceptance" })).toBeNull();
      expect(screen.queryByText(/Mechanics saved/i)).toBeNull();
    });

    it("restores dispatched_unknown after reload and resumes the same operation", async () => {
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_reload_unknown", "op_reload_unknown");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      const getOpSpy = vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue({
        schema: "dmb_read_acceptance_operation_response_v1",
        draft_id: "td_reload_unknown",
        result_label: "dispatched_unknown",
        operation: {
          schema: "dmb_statblock_acceptance_operation_v1",
          operation_id: "op_reload_unknown",
          idempotency_key: "idem_1",
          create_request_digest: `sha256:${"b".repeat(64)}`,
          request_body: {},
          source_draft_id: "td_reload_unknown",
          source_draft_version: 1,
          validation_receipt_digest: PREVIEW_DIGEST,
          authority_state: "dispatched_unknown",
          materialization: { draft_ref: "missing" },
          created_at: "2026-07-25T00:00:00Z",
          updated_at: "2026-07-25T00:00:00Z",
        },
      });
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics");
      const uuidSpy = vi.spyOn(crypto, "randomUUID");
      const reconcileSpy = vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_reload_unknown",
        operation_id: "op_reload_unknown",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_unknown_recovered",
          revision_id: "rev_unknown_recovered",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await user.type(screen.getByPlaceholderText("td_…"), "td_reload_unknown");

      await waitFor(() => {
        expect(getOpSpy).toHaveBeenCalledWith("td_reload_unknown", "op_reload_unknown");
      });
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-retry")).toBeTruthy();
      });
      expect(screen.queryByText(/Mechanics saved/i)).toBeNull();
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(uuidSpy).not.toHaveBeenCalled();
      expect(acceptSpy).not.toHaveBeenCalled();

      await user.click(screen.getByTestId("accept-mechanics-retry"));
      await waitFor(() => {
        expect(reconcileSpy).toHaveBeenCalledWith("td_reload_unknown", "op_reload_unknown");
      });
      expect(acceptSpy).not.toHaveBeenCalled();
      expect(uuidSpy).not.toHaveBeenCalled();
    });

    it("restores server_committed_reference_pending after reload without claiming mechanics_saved", async () => {
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_reload_pending", "op_reload_pending");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue({
        schema: "dmb_read_acceptance_operation_response_v1",
        draft_id: "td_reload_pending",
        result_label: "server_committed_reference_pending",
        operation: {
          schema: "dmb_statblock_acceptance_operation_v1",
          operation_id: "op_reload_pending",
          idempotency_key: "idem_2",
          create_request_digest: `sha256:${"c".repeat(64)}`,
          request_body: {},
          source_draft_id: "td_reload_pending",
          source_draft_version: 1,
          validation_receipt_digest: PREVIEW_DIGEST,
          authority_state: "server_committed",
          locator: {
            provider: "dungeonmind",
            statblock_id: "sb_pending",
            revision_id: "rev_pending",
            contract: "dungeonbuddy-statblocks-v1",
            contract_version: "1",
            definition_digest: PREVIEW_DIGEST,
          },
          materialization: { draft_ref: "missing" },
          created_at: "2026-07-25T00:00:00Z",
          updated_at: "2026-07-25T00:00:00Z",
        },
      });
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics");
      const uuidSpy = vi.spyOn(crypto, "randomUUID");
      const reconcileSpy = vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_reload_pending",
        operation_id: "op_reload_pending",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_pending",
          revision_id: "rev_pending",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await user.type(screen.getByPlaceholderText("td_…"), "td_reload_pending");

      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-reconcile")).toBeTruthy();
      });
      const flow = screen.getByTestId("accept-mechanics-flow");
      expect(flow.textContent).toMatch(/ThreatDraft attachment is still pending/i);
      expect(flow.textContent).not.toMatch(/Mechanics saved/i);
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(uuidSpy).not.toHaveBeenCalled();
      expect(acceptSpy).not.toHaveBeenCalled();

      await user.click(screen.getByTestId("accept-mechanics-reconcile"));
      await waitFor(() => {
        expect(reconcileSpy).toHaveBeenCalledWith("td_reload_pending", "op_reload_pending");
      });
      expect(acceptSpy).not.toHaveBeenCalled();
    });

    it("restores mechanics_saved locator after reload without minting a second operation", async () => {
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_reload_saved", "op_reload_saved");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue({
        schema: "dmb_read_acceptance_operation_response_v1",
        draft_id: "td_reload_saved",
        result_label: "mechanics_saved",
        operation: {
          schema: "dmb_statblock_acceptance_operation_v1",
          operation_id: "op_reload_saved",
          idempotency_key: "idem_3",
          create_request_digest: `sha256:${"d".repeat(64)}`,
          request_body: {},
          source_draft_id: "td_reload_saved",
          source_draft_version: 1,
          validation_receipt_digest: PREVIEW_DIGEST,
          authority_state: "reconciled",
          locator: {
            provider: "dungeonmind",
            statblock_id: "sb_exact",
            revision_id: "rev_exact",
            contract: "dungeonbuddy-statblocks-v1",
            contract_version: "1",
            definition_digest: PREVIEW_DIGEST,
          },
          materialization: { draft_ref: "attached" },
          created_at: "2026-07-25T00:00:00Z",
          updated_at: "2026-07-25T00:00:00Z",
        },
      });
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics");
      const uuidSpy = vi.spyOn(crypto, "randomUUID");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await user.type(screen.getByPlaceholderText("td_…"), "td_reload_saved");

      await waitFor(() => {
        expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
      });
      const locator = screen.getByTestId("accept-mechanics-locator");
      expect(locator.textContent).toMatch(/sb_exact/);
      expect(locator.textContent).toMatch(/rev_exact/);
      expect(locator.textContent).toMatch(PREVIEW_DIGEST);
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(screen.queryByRole("button", { name: "Reconcile acceptance" })).toBeNull();
      expect(uuidSpy).not.toHaveBeenCalled();
      expect(acceptSpy).not.toHaveBeenCalled();
    });

    async function setDraftId(
      user: ReturnType<typeof userEvent.setup>,
      draftId: string,
    ) {
      const input = screen.getByPlaceholderText("td_…");
      await user.clear(input);
      if (draftId) {
        await user.type(input, draftId);
      }
    }

    function pendingOperation(
      draftId: string,
      operationId: string,
      resultLabel:
        | "dispatched_unknown"
        | "server_committed_reference_pending"
        | "mechanics_saved"
        | "terminal_failure" = "server_committed_reference_pending",
    ) {
      const authority =
        resultLabel === "dispatched_unknown"
          ? "dispatched_unknown"
          : resultLabel === "mechanics_saved"
            ? "reconciled"
            : resultLabel === "terminal_failure"
              ? "terminal_failure"
              : "server_committed";
      return {
        schema: "dmb_read_acceptance_operation_response_v1" as const,
        draft_id: draftId,
        result_label: resultLabel,
        operation: {
          schema: "dmb_statblock_acceptance_operation_v1" as const,
          operation_id: operationId,
          idempotency_key: `idem_${operationId}`,
          create_request_digest: `sha256:${"e".repeat(64)}`,
          request_body: {},
          source_draft_id: draftId,
          source_draft_version: 1,
          validation_receipt_digest: PREVIEW_DIGEST,
          authority_state: authority as
            | "dispatched_unknown"
            | "server_committed"
            | "reconciled"
            | "terminal_failure",
          locator:
            resultLabel === "dispatched_unknown"
              ? null
              : {
                  provider: "dungeonmind" as const,
                  statblock_id: `sb_${operationId}`,
                  revision_id: `rev_${operationId}`,
                  contract: "dungeonbuddy-statblocks-v1",
                  contract_version: "1",
                  definition_digest: PREVIEW_DIGEST,
                },
          materialization: {
            draft_ref:
              resultLabel === "mechanics_saved"
                ? ("attached" as const)
                : ("missing" as const),
          },
          created_at: "2026-07-25T00:00:00Z",
          updated_at: "2026-07-25T00:00:00Z",
        },
      };
    }

    it("clears draft A pending state when switching to draft B with no stored operation", async () => {
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_draft_a", "op_a");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(liveApi, "getAcceptanceOperation").mockImplementation(async (draftId, opId) => {
        if (draftId === "td_draft_a" && opId === "op_a") {
          return pendingOperation("td_draft_a", "op_a");
        }
        return {
          schema: "dmb_read_acceptance_operation_response_v1",
          draft_id: draftId,
          operation: null,
          result_label: null,
        };
      });
      const reconcileSpy = vi.spyOn(liveApi, "reconcileAcceptanceOperation");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_draft_a");
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-reconcile")).toBeTruthy();
      });

      await setDraftId(user, "td_draft_b");
      await waitFor(() => {
        expect(screen.queryByTestId("accept-mechanics-reconcile")).toBeNull();
        expect(screen.queryByText(/ThreatDraft attachment is still pending/i)).toBeNull();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_draft_b")).toBeNull();
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_draft_a")).toBe("op_a");

      await validateWorkingCopy(user);
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeTruthy();
      expect(reconcileSpy).not.toHaveBeenCalled();
    });

    it("restores distinct operations when switching between draft A and draft B", async () => {
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_draft_a", "op_a");
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_draft_b", "op_b");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "getAcceptanceOperation").mockImplementation(async (draftId, opId) => {
        if (draftId === "td_draft_a" && opId === "op_a") {
          return pendingOperation("td_draft_a", "op_a");
        }
        if (draftId === "td_draft_b" && opId === "op_b") {
          return pendingOperation("td_draft_b", "op_b");
        }
        throw new Error(`unexpected getAcceptanceOperation(${draftId}, ${opId})`);
      });
      const reconcileSpy = vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_draft_b",
        operation_id: "op_b",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_op_b",
          revision_id: "rev_op_b",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_draft_a");
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-reconcile")).toBeTruthy();
      });

      await setDraftId(user, "td_draft_b");
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-reconcile")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-reconcile"));
      await waitFor(() => {
        expect(reconcileSpy).toHaveBeenCalledWith("td_draft_b", "op_b");
      });
      expect(reconcileSpy).not.toHaveBeenCalledWith("td_draft_b", "op_a");
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_draft_b")).toBe("op_b");
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_draft_a")).toBe("op_a");
    });

    it("ignores stale restore response after draft ID changes and releases restorePending", async () => {
      let resolveRestoreA!: (value: ReturnType<typeof pendingOperation>) => void;
      const restoreAPromise = new Promise<ReturnType<typeof pendingOperation>>((resolve) => {
        resolveRestoreA = resolve;
      });

      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_stale_a", "op_stale_a");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(liveApi, "getAcceptanceOperation").mockImplementation(async (draftId, opId) => {
        if (draftId === "td_stale_a" && opId === "op_stale_a") {
          return restoreAPromise;
        }
        return {
          schema: "dmb_read_acceptance_operation_response_v1",
          draft_id: draftId,
          operation: null,
          result_label: null,
        };
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_stale_a");
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-restoring")).toBeTruthy();
      });
      await setDraftId(user, "td_stale_b");
      await waitFor(() => {
        expect(screen.queryByTestId("accept-mechanics-restoring")).toBeNull();
      });
      resolveRestoreA(pendingOperation("td_stale_a", "op_stale_a"));
      await waitFor(() => {
        expect(screen.queryByText(/ThreatDraft attachment is still pending/i)).toBeNull();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_stale_b")).toBeNull();
      await validateWorkingCopy(user);
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeTruthy();
    });

    it("ignores stale accept response after draft ID changes", async () => {
      let resolveAccept!: (value: AcceptThreatDraftMechanicsResponseV1) => void;
      const acceptPromise = new Promise<AcceptThreatDraftMechanicsResponseV1>((resolve) => {
        resolveAccept = resolve;
      });

      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_accept_race");
      vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockImplementation(async () => acceptPromise);

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_accept_race");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

      await setDraftId(user, "td_accept_other");
      resolveAccept({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_accept_race",
        operation_id: "op_accept_race",
        result_label: "server_committed_reference_pending",
        authority_state: "server_committed",
      });

      await waitFor(() => {
        expect(screen.queryByTestId("accept-mechanics-reconcile")).toBeNull();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_accept_other")).toBeNull();
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_accept_race")).toBe(
        "op_accept_race",
      );
    });

    it("ignores stale reconcile response after draft ID changes", async () => {
      let resolveReconcile!: (value: AcceptThreatDraftMechanicsResponseV1) => void;
      const reconcilePromise = new Promise<AcceptThreatDraftMechanicsResponseV1>((resolve) => {
        resolveReconcile = resolve;
      });

      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_rec_a", "op_rec_a");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue(
        pendingOperation("td_rec_a", "op_rec_a", "dispatched_unknown"),
      );
      vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockImplementation(
        async () => reconcilePromise,
      );

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_rec_a");
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-retry")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-retry"));
      await setDraftId(user, "td_rec_b");
      resolveReconcile({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_rec_a",
        operation_id: "op_rec_a",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_op_rec_a",
          revision_id: "rev_op_rec_a",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      await waitFor(() => {
        expect(screen.queryByText(/Mechanics saved; not published/i)).toBeNull();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_rec_b")).toBeNull();
    });

    it.each([
      ["acceptance_blocked", "ephemeral"],
      ["acceptance_busy", "ephemeral"],
      ["acceptance_history_full", "ephemeral"],
      ["acceptance_input_conflict", "same_op"],
      ["acceptance_draft_unavailable", "same_op"],
      ["dispatched_unknown", "same_op_unknown"],
      ["server_committed_reference_pending", "same_op_pending"],
      ["accepted_ref_conflict", "bound_conflict"],
      ["mechanics_saved", "bound_saved"],
      ["terminal_failure", "terminal"],
    ] as const)(
      "classifies result_label %s for actions and storage (%s)",
      async (resultLabel, kind) => {
        vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
        vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(
          successValidate("valid"),
        );
        vi.spyOn(crypto, "randomUUID").mockReturnValue("op_label_case");
        vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_label",
          operation_id: "op_label_case",
          result_label: resultLabel,
          authority_state:
            resultLabel === "dispatched_unknown"
              ? "dispatched_unknown"
              : resultLabel === "mechanics_saved"
                ? "reconciled"
                : resultLabel === "terminal_failure"
                  ? "terminal_failure"
                  : "server_committed",
          draft_ref: resultLabel === "accepted_ref_conflict" ? "conflicted" : "missing",
          message: `msg_${resultLabel}`,
          locator:
            resultLabel === "mechanics_saved"
              ? {
                  provider: "dungeonmind",
                  statblock_id: "sb_label",
                  revision_id: "rev_label",
                  contract: "dungeonbuddy-statblocks-v1",
                  contract_version: "1",
                  definition_digest: PREVIEW_DIGEST,
                }
              : null,
        });
        vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockResolvedValue({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_label",
          operation_id: "op_label_case",
          result_label: "mechanics_saved",
          locator: {
            provider: "dungeonmind",
            statblock_id: "sb_label",
            revision_id: "rev_label",
            contract: "dungeonbuddy-statblocks-v1",
            contract_version: "1",
            definition_digest: PREVIEW_DIGEST,
          },
        });

        const user = await loadId("cand_fixture1");
        await waitFor(() => {
          expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
        });
        await setDraftId(user, "td_label");
        await validateWorkingCopy(user);
        await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

        await waitFor(() => {
          expect(document.querySelector(`[data-accept-result="${resultLabel}"]`)).toBeTruthy();
        });

        const stored = sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_label");

        if (kind === "ephemeral") {
          expect(stored).toBeNull();
          expect(screen.getByTestId("accept-ephemeral-block")).toBeTruthy();
          expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeTruthy();
          expect(screen.queryByTestId("accept-mechanics-reconcile")).toBeNull();
          expect(screen.queryByTestId("accept-mechanics-retry")).toBeNull();
          expect(screen.queryByTestId("accept-mechanics-same-op-recover")).toBeNull();
          expect(screen.queryByText(/Mechanics saved/i)).toBeNull();
        } else if (kind === "same_op") {
          expect(stored).toBe("op_label_case");
          expect(screen.getByTestId("accept-mechanics-same-op-recover")).toBeTruthy();
          expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
        } else if (kind === "same_op_unknown") {
          expect(stored).toBe("op_label_case");
          expect(screen.getByTestId("accept-mechanics-retry")).toBeTruthy();
          expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
          expect(screen.queryByText(/Mechanics saved/i)).toBeNull();
        } else if (kind === "same_op_pending") {
          expect(stored).toBe("op_label_case");
          expect(screen.getByTestId("accept-mechanics-reconcile")).toBeTruthy();
          expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
          expect(screen.queryByText(/Mechanics saved/i)).toBeNull();
        } else if (kind === "bound_conflict") {
          expect(stored).toBe("op_label_case");
          expect(screen.getByTestId("accept-ref-conflict")).toBeTruthy();
          expect(screen.queryByRole("button", { name: "Reconcile acceptance" })).toBeNull();
          expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
          expect(screen.queryByText(/Mechanics saved/i)).toBeNull();
        } else if (kind === "bound_saved") {
          expect(stored).toBe("op_label_case");
          expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
          expect(screen.getByTestId("accept-mechanics-locator").textContent).toMatch(/sb_label/);
          expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
        } else if (kind === "terminal") {
          expect(stored).toBe("op_label_case");
          expect(screen.getByTestId("accept-terminal-failure")).toBeTruthy();
          expect(screen.queryByRole("button", { name: "Retry accept" })).toBeNull();
          expect(screen.getByTestId("accept-mechanics-start-new")).toBeTruthy();
          vi.spyOn(crypto, "randomUUID").mockReturnValue("op_label_new");
          await user.click(screen.getByTestId("accept-mechanics-start-new"));
          expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_label")).toBeNull();
          expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeTruthy();
          await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
          await waitFor(() => {
            expect(liveApi.acceptThreatDraftMechanics).toHaveBeenCalled();
          });
          const lastCall = vi.mocked(liveApi.acceptThreatDraftMechanics).mock.calls.at(-1);
          expect(lastCall?.[1].operation_id).toBe("op_label_new");
          expect(lastCall?.[1].operation_id).not.toBe("op_label_case");
        }
      },
    );

    it("retains optimistic operation id across reload-before-claim miss then finds it on retry", async () => {
      ACCEPT_RESTORE_LOOKUP.maxAttempts = 3;
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_race_claim", "op_race_claim");
      let lookups = 0;
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      const getOpSpy = vi.spyOn(liveApi, "getAcceptanceOperation").mockImplementation(async () => {
        lookups += 1;
        if (lookups < 3) {
          return {
            schema: "dmb_read_acceptance_operation_response_v1",
            draft_id: "td_race_claim",
            operation: null,
            result_label: null,
          };
        }
        return pendingOperation("td_race_claim", "op_race_claim", "dispatched_unknown");
      });
      const uuidSpy = vi.spyOn(crypto, "randomUUID");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_race_claim");

      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-retry")).toBeTruthy();
      });
      expect(getOpSpy.mock.calls.length).toBeGreaterThanOrEqual(3);
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_race_claim")).toBe(
        "op_race_claim",
      );
      expect(uuidSpy).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
    });

    it("does not clear optimistic id after bounded restore misses while claim may still be in flight", async () => {
      ACCEPT_RESTORE_LOOKUP.maxAttempts = 3;
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_miss", "op_miss_inflight");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      const getOpSpy = vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue({
        schema: "dmb_read_acceptance_operation_response_v1",
        draft_id: "td_miss",
        operation: null,
        result_label: null,
      });
      const uuidSpy = vi.spyOn(crypto, "randomUUID");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_miss");

      await waitFor(() => {
        expect(screen.getByTestId("accept-existence-unresolved")).toBeTruthy();
      });
      expect(getOpSpy).toHaveBeenCalledTimes(3);
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_miss")).toBe("op_miss_inflight");
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(uuidSpy).not.toHaveBeenCalled();

      // A later lookup can still attach without minting a replacement UUID.
      getOpSpy.mockResolvedValue(
        pendingOperation("td_miss", "op_miss_inflight", "server_committed_reference_pending"),
      );
      await user.click(screen.getByTestId("accept-mechanics-retry-lookup"));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-reconcile")).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_miss")).toBe("op_miss_inflight");
      expect(uuidSpy).not.toHaveBeenCalled();
    });

    it("treats fresh validation acceptance_blocked as ephemeral and clears the attempted id", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_fresh_blocked");
      vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_fresh_blocked",
        operation_id: "op_fresh_blocked",
        result_label: "acceptance_blocked",
        message: "expected draft version mismatch",
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_fresh_blocked");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

      await waitFor(() => {
        expect(screen.getByTestId("accept-ephemeral-block")).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_fresh_blocked")).toBeNull();
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeTruthy();
      expect(screen.queryByTestId("accept-mechanics-same-op-recover")).toBeNull();
    });

    it("keeps operation id after replay validation rejection when journal lookup returns null", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_replay_valid_fail");
      const acceptSpy = vi
        .spyOn(liveApi, "acceptThreatDraftMechanics")
        .mockRejectedValueOnce(new Error("Failed to fetch"))
        .mockResolvedValueOnce({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_replay_valid_fail",
          operation_id: "op_replay_valid_fail",
          result_label: "acceptance_blocked",
          message: "acceptance blocked: definition failed authoritative validation",
        });
      vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue({
        schema: "dmb_read_acceptance_operation_response_v1",
        draft_id: "td_replay_valid_fail",
        operation: null,
        result_label: null,
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_replay_valid_fail");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-replay")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-replay"));

      await waitFor(() => {
        expect(screen.getByTestId("accept-existence-unresolved")).toBeTruthy();
      });
      // Null journal reads are not proof the original POST cannot claim — no replacement UUID.
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_replay_valid_fail")).toBe(
        "op_replay_valid_fail",
      );
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(screen.queryByTestId("accept-mechanics-abandon")).toBeNull();
      expect(screen.queryByTestId("accept-mechanics-start-new")).toBeNull();
      expect(acceptSpy).toHaveBeenCalledTimes(2);
      expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    });

    it("does not orphan a still-claiming operation via local abandon", async () => {
      ACCEPT_RESTORE_LOOKUP.maxAttempts = 3;
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_no_local_abandon");
      vi.spyOn(liveApi, "acceptThreatDraftMechanics")
        .mockRejectedValueOnce(new Error("Failed to fetch"))
        .mockResolvedValueOnce({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_no_local_abandon",
          operation_id: "op_no_local_abandon",
          result_label: "acceptance_blocked",
          message: "acceptance journal temporarily unavailable",
        });
      let lookups = 0;
      vi.spyOn(liveApi, "getAcceptanceOperation").mockImplementation(async () => {
        lookups += 1;
        if (lookups <= ACCEPT_RESTORE_LOOKUP.maxAttempts) {
          return {
            schema: "dmb_read_acceptance_operation_response_v1",
            draft_id: "td_no_local_abandon",
            operation: null,
            result_label: null,
          };
        }
        // Original POST continues server-side and eventually claims.
        return pendingOperation(
          "td_no_local_abandon",
          "op_no_local_abandon",
          "server_committed_reference_pending",
        );
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_no_local_abandon");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-replay")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-replay"));
      await waitFor(() => {
        expect(screen.getByTestId("accept-existence-unresolved")).toBeTruthy();
      });

      // No local abandon / replacement UUID while the original POST may still claim.
      expect(screen.queryByTestId("accept-mechanics-abandon")).toBeNull();
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(screen.queryByTestId("accept-mechanics-start-new")).toBeNull();
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_no_local_abandon")).toBe(
        "op_no_local_abandon",
      );
      expect(document.body.textContent).not.toMatch(/explicitly closes this operation/i);

      // Eventual durable claim remains recoverable through the retained pointer.
      await user.click(screen.getByTestId("accept-mechanics-retry-lookup"));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-reconcile")).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_no_local_abandon")).toBe(
        "op_no_local_abandon",
      );
      expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    });

    it("keeps operation id after replay version mismatch when journal lookup returns null", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_replay_version");
      vi.spyOn(liveApi, "acceptThreatDraftMechanics")
        .mockRejectedValueOnce(new Error("Failed to fetch"))
        .mockResolvedValueOnce({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_replay_version",
          operation_id: "op_replay_version",
          result_label: "acceptance_blocked",
          message: "expected draft version mismatch",
        });
      const getOpSpy = vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue({
        schema: "dmb_read_acceptance_operation_response_v1",
        draft_id: "td_replay_version",
        operation: null,
        result_label: null,
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_replay_version");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-replay")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-replay"));

      await waitFor(() => {
        expect(screen.getByTestId("accept-existence-unresolved")).toBeTruthy();
      });
      expect(getOpSpy.mock.calls.length).toBeGreaterThanOrEqual(ACCEPT_RESTORE_LOOKUP.maxAttempts);
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_replay_version")).toBe(
        "op_replay_version",
      );
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    });

    it("retains id when original POST may still claim after client transport failure", async () => {
      ACCEPT_RESTORE_LOOKUP.maxAttempts = 3;
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_inflight_claim");
      vi.spyOn(liveApi, "acceptThreatDraftMechanics")
        .mockRejectedValueOnce(new Error("Failed to fetch"))
        .mockResolvedValueOnce({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_inflight_claim",
          operation_id: "op_inflight_claim",
          result_label: "acceptance_blocked",
          message: "acceptance journal temporarily unavailable",
        });
      let lookups = 0;
      const getOpSpy = vi.spyOn(liveApi, "getAcceptanceOperation").mockImplementation(async () => {
        lookups += 1;
        // Replay's claim-evidence lookups return null before the original server claim lands.
        if (lookups <= ACCEPT_RESTORE_LOOKUP.maxAttempts) {
          return {
            schema: "dmb_read_acceptance_operation_response_v1",
            draft_id: "td_inflight_claim",
            operation: null,
            result_label: null,
          };
        }
        return pendingOperation("td_inflight_claim", "op_inflight_claim", "dispatched_unknown");
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_inflight_claim");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-replay")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-replay"));

      await waitFor(() => {
        expect(screen.getByTestId("accept-existence-unresolved")).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_inflight_claim")).toBe(
        "op_inflight_claim",
      );
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(crypto.randomUUID).toHaveBeenCalledTimes(1);

      // Eventual original claim remains recoverable without a replacement UUID.
      await user.click(screen.getByTestId("accept-mechanics-retry-lookup"));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-retry")).toBeTruthy();
      });
      expect(getOpSpy.mock.calls.length).toBeGreaterThan(ACCEPT_RESTORE_LOOKUP.maxAttempts);
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_inflight_claim")).toBe(
        "op_inflight_claim",
      );
      expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    });

    it("retains id when replay is blocked but journal already has the operation", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_replay_present");
      vi.spyOn(liveApi, "acceptThreatDraftMechanics")
        .mockRejectedValueOnce(new Error("Failed to fetch"))
        .mockResolvedValueOnce({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_replay_present",
          operation_id: "op_replay_present",
          result_label: "acceptance_blocked",
          message: "acceptance journal temporarily unavailable",
        });
      vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue(
        pendingOperation("td_replay_present", "op_replay_present", "dispatched_unknown"),
      );

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_replay_present");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-replay")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-replay"));

      await waitFor(() => {
        expect(screen.getByTestId("accept-blocked-recovery")).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_replay_present")).toBe(
        "op_replay_present",
      );
      expect(screen.getByTestId("accept-mechanics-same-op-recover")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
    });

    it("retains id when replay is blocked and journal lookup is uncertain", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_replay_uncertain");
      vi.spyOn(liveApi, "acceptThreatDraftMechanics")
        .mockRejectedValueOnce(new Error("Failed to fetch"))
        .mockResolvedValueOnce({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_replay_uncertain",
          operation_id: "op_replay_uncertain",
          result_label: "acceptance_blocked",
          message: "acceptance journal temporarily unavailable",
        });
      vi.spyOn(liveApi, "getAcceptanceOperation").mockRejectedValue(
        new Error("journal storage unavailable"),
      );

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_replay_uncertain");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-replay")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-replay"));

      await waitFor(() => {
        expect(screen.getByTestId("accept-existence-unresolved")).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_replay_uncertain")).toBe(
        "op_replay_uncertain",
      );
      expect(screen.getByTestId("accept-mechanics-replay")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
    });

    it("retains operation id when recovery returns acceptance_blocked for journal unavailability", async () => {
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_rec_blocked", "op_rec_blocked");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue(
        pendingOperation("td_rec_blocked", "op_rec_blocked", "dispatched_unknown"),
      );
      vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_rec_blocked",
        operation_id: "op_rec_blocked",
        result_label: "acceptance_blocked",
        message: "acceptance journal temporarily unavailable",
      });
      const uuidSpy = vi.spyOn(crypto, "randomUUID");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_rec_blocked");
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-retry")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-retry"));

      await waitFor(() => {
        expect(screen.getByTestId("accept-blocked-recovery")).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_rec_blocked")).toBe(
        "op_rec_blocked",
      );
      expect(screen.getByTestId("accept-mechanics-same-op-recover")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(uuidSpy).not.toHaveBeenCalled();
    });

    it("preserves operation id across transient reconcile transport failures", async () => {
      sessionStorage.setItem("dmb.sbw07.acceptOperationId:td_rec_transport", "op_rec_transport");
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue(
        pendingOperation("td_rec_transport", "op_rec_transport"),
      );
      vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockRejectedValue(
        new Error("network down"),
      );
      const uuidSpy = vi.spyOn(crypto, "randomUUID");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_rec_transport");
      await waitFor(() => {
        expect(screen.getByTestId("accept-mechanics-reconcile")).toBeTruthy();
      });
      await user.click(screen.getByTestId("accept-mechanics-reconcile"));

      await waitFor(() => {
        expect(screen.getByTestId("accept-existence-unresolved")).toBeTruthy();
      });
      expect(screen.getByText(/network down/i)).toBeTruthy();
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_rec_transport")).toBe(
        "op_rec_transport",
      );
      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeDisabled();
      expect(uuidSpy).not.toHaveBeenCalled();
    });

    it("replays exact Accept body when the request never reached the backend", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_transport_miss");
      const acceptSpy = vi
        .spyOn(liveApi, "acceptThreatDraftMechanics")
        .mockRejectedValueOnce(new Error("Failed to fetch"))
        .mockResolvedValueOnce({
          schema: "dmb_accept_threat_draft_mechanics_response_v1",
          draft_id: "td_transport_miss",
          operation_id: "op_transport_miss",
          result_label: "mechanics_saved",
          locator: {
            provider: "dungeonmind",
            statblock_id: "sb_replay",
            revision_id: "rev_replay",
            contract: "dungeonbuddy-statblocks-v1",
            contract_version: "1",
            definition_digest: PREVIEW_DIGEST,
          },
        });
      vi.spyOn(liveApi, "getAcceptanceOperation").mockResolvedValue({
        schema: "dmb_read_acceptance_operation_response_v1",
        draft_id: "td_transport_miss",
        operation: null,
        result_label: null,
      });
      const reconcileSpy = vi.spyOn(liveApi, "reconcileAcceptanceOperation").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_transport_miss",
        operation_id: "op_transport_miss",
        result_label: "acceptance_blocked",
        message: "acceptance operation not found",
      });

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_transport_miss");
      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

      await waitFor(() => {
        expect(screen.getByTestId("accept-existence-unresolved")).toBeTruthy();
      });
      expect(screen.getByText(/Failed to fetch/i)).toBeTruthy();
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_transport_miss")).toBe(
        "op_transport_miss",
      );
      expect(screen.getByTestId("accept-mechanics-replay")).toBeTruthy();
      expect(screen.getByTestId("accept-mechanics-resume-unresolved")).toBeTruthy();

      // Reconcile alone cannot claim a never-begun operation.
      await user.click(screen.getByTestId("accept-mechanics-resume-unresolved"));
      await waitFor(() => {
        expect(reconcileSpy).toHaveBeenCalledWith("td_transport_miss", "op_transport_miss");
      });
      await waitFor(() => {
        expect(screen.getByTestId("accept-blocked-recovery")).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_transport_miss")).toBe(
        "op_transport_miss",
      );

      await user.click(screen.getByTestId("accept-mechanics-replay"));
      await waitFor(() => {
        expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
      });
      expect(acceptSpy).toHaveBeenCalledTimes(2);
      expect(acceptSpy.mock.calls[1][1].operation_id).toBe("op_transport_miss");
      expect(acceptSpy.mock.calls[1][1].validation_definition_digest).toBe(PREVIEW_DIGEST);
      expect(acceptSpy.mock.calls[1][1].expected_draft_version).toBe(1);
      expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    });

    it("keeps committed operation recoverable when a duplicate confirm is attempted", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      vi.spyOn(crypto, "randomUUID").mockReturnValue("op_dup_guard");
      let resolveAccept!: (value: AcceptThreatDraftMechanicsResponseV1) => void;
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveAccept = resolve;
          }),
      );

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await setDraftId(user, "td_dup_guard");
      await validateWorkingCopy(user);
      const acceptButton = screen.getByRole("button", { name: "Accept/Save mechanics" });
      await user.click(acceptButton);
      await waitFor(() => {
        expect(acceptButton).toBeDisabled();
      });
      await user.click(acceptButton);
      expect(acceptSpy).toHaveBeenCalledTimes(1);

      resolveAccept({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: "td_dup_guard",
        operation_id: "op_dup_guard",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_dup",
          revision_id: "rev_dup",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });
      await waitFor(() => {
        expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
      });
      expect(sessionStorage.getItem("dmb.sbw07.acceptOperationId:td_dup_guard")).toBe("op_dup_guard");
      expect(acceptSpy).toHaveBeenCalledTimes(1);
      expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    });
  });

  describe("create-and-generate", () => {
    const DRAFT_ID = "11111111-1111-4111-8111-111111111111";
    const THREAT_DESCRIPTION =
      "Mireward Latchling\nA reed-choked latching scavenger from the Mireward verge.";

    async function fillRequiredCreateFields(user: ReturnType<typeof userEvent.setup>) {
      await user.type(screen.getByTestId("create-threat-description"), THREAT_DESCRIPTION);
    }

    function mockCreatedDraft(overrides?: Partial<{ draft_id: string; version: number; name: string }>) {
      return {
        schema: "dmb_threat_draft_v1" as const,
        draft_id: overrides?.draft_id ?? DRAFT_ID,
        version: overrides?.version ?? 1,
        world_id: "eldyrwild",
        campaign_id: "longmont-c2",
        name: overrides?.name ?? "Mireward Latchling",
        description: THREAT_DESCRIPTION,
        threat_kind: "creature",
        workflow_state: "drafting" as const,
        created_by: "gm",
        created_at: "2026-07-26T00:00:00Z",
        updated_at: "2026-07-26T00:00:00Z",
      };
    }

    it("creates a draft then generates and loads using the returned identity", async () => {
      const user = userEvent.setup();
      const createSpy = vi.spyOn(liveApi, "createThreatDraft").mockResolvedValue(mockCreatedDraft());
      const generateSpy = vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
        schema: "dmb_generate_threat_draft_candidate_response_v1",
        draft_id: DRAFT_ID,
        generated_from_draft_version: 1,
        request_id: "req_create_gen",
        outcome: "success",
        candidate,
        cache_status: "stored",
        persistence_failures: [],
      });
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

      render(<StatblockWorkbenchModule />);
      expect(screen.getByTestId("create-threat-context-binding").textContent).toMatch(
        /eldyrwild.*longmont-c2.*dnd5e.*2024/i,
      );
      expect(screen.queryByTestId("create-threat-world-id")).toBeNull();
      expect(screen.queryByTestId("create-threat-name")).toBeNull();
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));

      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      expect(createSpy).toHaveBeenCalledTimes(1);
      const createBody = createSpy.mock.calls[0][0];
      expect(createBody.name).toBe("Mireward Latchling");
      expect(createBody.threat_kind).toBe("creature");
      expect(createBody.created_by).toBe("gm");
      expect(createBody.world_id).toBe("eldyrwild");
      expect(createBody.campaign_id).toBe("longmont-c2");
      expect(createBody.graph_context_snapshot.graph_revision_id).toBe("rev_live_control_eldyrwild");
      expect(createBody.graph_context_snapshot.selected_node_ids).toEqual([]);
      expect(createBody.graph_context_snapshot.admitted_source_anchor_ids).toEqual([]);
      expect(createBody.generation_intent.ruleset).toEqual({
        system: "dnd5e",
        edition: "2024",
        house_ruleset_id: null,
      });
      expect(createBody.intended_roles).toEqual([]);
      expect(createBody.tags).toEqual([]);
      expect(createBody.generation_intent.must_include).toEqual([]);
      expect(createBody.generation_intent.must_avoid).toEqual([]);
      expect(JSON.stringify(createBody)).not.toMatch(/rev_workbench_quick_create|demo|latest|"current"/i);
      expect(generateSpy).toHaveBeenCalledWith(DRAFT_ID, { expected_draft_version: 1 });
      expect(liveApi.getStatblockCandidate).toHaveBeenCalledWith("cand_fixture1");
      expect(screen.queryByTestId("created-draft-identity")).toBeNull();
      expect(screen.queryByTestId("create-threat-status")).toBeNull();
      expect(screen.getByPlaceholderText("td_…")).toHaveProperty("value", DRAFT_ID);
    });

    it("accepts mechanics from create-and-generate without typing Advanced draft fields", async () => {
      const user = userEvent.setup();
      vi.spyOn(liveApi, "createThreatDraft").mockResolvedValue(mockCreatedDraft());
      vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
        schema: "dmb_generate_threat_draft_candidate_response_v1",
        draft_id: DRAFT_ID,
        generated_from_draft_version: 1,
        request_id: "req_create_accept",
        outcome: "success",
        candidate,
        cache_status: "stored",
        persistence_failures: [],
      });
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: DRAFT_ID,
        operation_id: "op_create_accept",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_create",
          revision_id: "rev_create",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });

      // Clear the Advanced recovery fields — happy path must use createdDraft identity.
      const draftInput = screen.getByPlaceholderText("td_…");
      await user.clear(draftInput);
      expect(draftInput).toHaveProperty("value", "");

      await validateWorkingCopy(user);
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));

      await waitFor(() => {
        expect(acceptSpy).toHaveBeenCalledTimes(1);
      });
      expect(acceptSpy.mock.calls[0][0]).toBe(DRAFT_ID);
      expect(acceptSpy.mock.calls[0][1].expected_draft_version).toBe(1);
      await waitFor(() => {
        expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
      });
    });

    it("derives a short name from prose starting with A … is", async () => {
      const user = userEvent.setup();
      const createSpy = vi.spyOn(liveApi, "createThreatDraft").mockResolvedValue(
        mockCreatedDraft({ name: "Mireward Latchling" }),
      );
      vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
        schema: "dmb_generate_threat_draft_candidate_response_v1",
        draft_id: DRAFT_ID,
        generated_from_draft_version: 1,
        request_id: "req_prose_name",
        outcome: "success",
        candidate,
        cache_status: "stored",
        persistence_failures: [],
      });
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

      render(<StatblockWorkbenchModule />);
      await user.type(
        screen.getByTestId("create-threat-description"),
        "A Mireward Latchling is the crawling siege-form of the Shepherd’s meat, a low horror.",
      );
      await user.click(screen.getByTestId("create-and-generate-submit"));

      await waitFor(() => {
        expect(createSpy).toHaveBeenCalled();
      });
      expect(createSpy.mock.calls[0][0].name).toBe("Mireward Latchling");
    });

    it("shows one generate-failure alert with the real error (not a stuck Generating…)", async () => {
      const user = userEvent.setup();
      vi.spyOn(liveApi, "createThreatDraft").mockResolvedValue(mockCreatedDraft());
      vi.spyOn(liveApi, "generateThreatDraftCandidate").mockRejectedValue(
        new Error("downstream_unavailable: Connection refused"),
      );

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));

      await waitFor(() => {
        expect(screen.getByTestId("created-draft-identity").textContent).toMatch(
          /Couldn’t generate a candidate for Mireward Latchling/i,
        );
      });
      expect(screen.getByTestId("created-draft-identity").textContent).toMatch(
        /downstream_unavailable|Connection refused/i,
      );
      expect(screen.getByTestId("created-draft-identity").getAttribute("data-draft-id")).toBe(DRAFT_ID);
      expect(screen.queryByTestId("create-threat-status")).toBeNull();
      expect(screen.getByTestId("retry-generate-created-draft")).toBeTruthy();
    });

    it("does not generate after a definite create failure", async () => {
      const user = userEvent.setup();
      vi.spyOn(liveApi, "createThreatDraft").mockRejectedValue(
        new liveApi.LiveApiError("invalid world_id", 422),
      );
      const generateSpy = vi.spyOn(liveApi, "generateThreatDraftCandidate");

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));

      await waitFor(() => {
        expect(screen.getByTestId("create-threat-error").textContent).toMatch(/Unable to create/i);
      });
      expect(generateSpy).not.toHaveBeenCalled();
    });

    it("retains created draft and retries generation without recreating", async () => {
      const user = userEvent.setup();
      const createSpy = vi.spyOn(liveApi, "createThreatDraft").mockResolvedValue(mockCreatedDraft());
      const generateSpy = vi
        .spyOn(liveApi, "generateThreatDraftCandidate")
        .mockRejectedValueOnce(new Error("server timeout"))
        .mockResolvedValueOnce({
          schema: "dmb_generate_threat_draft_candidate_response_v1",
          draft_id: DRAFT_ID,
          generated_from_draft_version: 1,
          request_id: "req_retry",
          outcome: "success",
          candidate,
          cache_status: "stored",
          persistence_failures: [],
        });
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));

      await waitFor(() => {
        expect(screen.getByTestId("retry-generate-created-draft")).toBeTruthy();
      });
      expect(createSpy).toHaveBeenCalledTimes(1);
      expect(generateSpy).toHaveBeenCalledTimes(1);

      await user.click(screen.getByTestId("retry-generate-created-draft"));
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      expect(createSpy).toHaveBeenCalledTimes(1);
      expect(generateSpy).toHaveBeenCalledTimes(2);
      expect(generateSpy).toHaveBeenNthCalledWith(2, DRAFT_ID, { expected_draft_version: 1 });
    });

    it("guards duplicate submit so at most one create runs", async () => {
      const user = userEvent.setup();
      let resolveCreate: (value: ReturnType<typeof mockCreatedDraft>) => void = () => {};
      const createSpy = vi.spyOn(liveApi, "createThreatDraft").mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveCreate = resolve;
          }),
      );
      vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
        schema: "dmb_generate_threat_draft_candidate_response_v1",
        draft_id: DRAFT_ID,
        generated_from_draft_version: 1,
        request_id: "req_dup",
        outcome: "success",
        candidate,
        cache_status: "stored",
        persistence_failures: [],
      });
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      const submit = screen.getByTestId("create-and-generate-submit");
      await user.click(submit);
      await user.click(submit);
      await waitFor(() => {
        expect(createSpy).toHaveBeenCalledTimes(1);
      });
      resolveCreate(mockCreatedDraft());
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      expect(createSpy).toHaveBeenCalledTimes(1);
    });

    it("ignores delayed create success after a newer manual load", async () => {
      const user = userEvent.setup();
      let resolveCreate: (value: ReturnType<typeof mockCreatedDraft>) => void = () => {};
      const createSpy = vi.spyOn(liveApi, "createThreatDraft").mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveCreate = resolve;
          }),
      );
      const generateSpy = vi.spyOn(liveApi, "generateThreatDraftCandidate");
      const candidateB: GeneratedStatblockCandidateV1 = {
        ...candidate,
        candidate_id: "cand_fixture2",
        definition: {
          ...candidate.definition,
          identity: { ...candidate.definition.identity, name: "Manual Selection" },
        },
      };
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
        schema: "dmb_statblock_candidate_read_v1",
        candidate_id: candidateB.candidate_id,
        status: "active",
        candidate: candidateB,
      });

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));
      await waitFor(() => {
        expect(createSpy).toHaveBeenCalled();
      });

      await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture2");
      await user.click(screen.getByRole("button", { name: "Load candidate" }));
      await waitFor(() => {
        expect(screen.getByDisplayValue("Manual Selection")).toBeTruthy();
      });

      resolveCreate(mockCreatedDraft());
      await waitFor(() => {
        expect(screen.getByDisplayValue("Manual Selection")).toBeTruthy();
      });
      expect(generateSpy).not.toHaveBeenCalled();
      expect(screen.queryByDisplayValue("Ironhide Brute")).toBeNull();
    });

    it("ignores delayed generation success after a newer manual load", async () => {
      const user = userEvent.setup();
      vi.spyOn(liveApi, "createThreatDraft").mockResolvedValue(mockCreatedDraft());
      let resolveGenerate: (value: GenerateThreatDraftCandidateResponseV1) => void = () => {};
      vi.spyOn(liveApi, "generateThreatDraftCandidate").mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveGenerate = resolve;
          }),
      );
      const candidateB: GeneratedStatblockCandidateV1 = {
        ...candidate,
        candidate_id: "cand_fixture2",
        definition: {
          ...candidate.definition,
          identity: { ...candidate.definition.identity, name: "Manual Selection" },
        },
      };
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
        schema: "dmb_statblock_candidate_read_v1",
        candidate_id: candidateB.candidate_id,
        status: "active",
        candidate: candidateB,
      });

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));
      await waitFor(() => {
        expect(liveApi.generateThreatDraftCandidate).toHaveBeenCalled();
      });

      await user.clear(screen.getByPlaceholderText("cand_…"));
      await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture2");
      await user.click(screen.getByRole("button", { name: "Load candidate" }));
      await waitFor(() => {
        expect(screen.getByDisplayValue("Manual Selection")).toBeTruthy();
      });

      resolveGenerate({
        schema: "dmb_generate_threat_draft_candidate_response_v1",
        draft_id: DRAFT_ID,
        generated_from_draft_version: 1,
        request_id: "req_stale_gen",
        outcome: "success",
        candidate,
        cache_status: "stored",
        persistence_failures: [],
      });

      await waitFor(() => {
        expect(screen.getByDisplayValue("Manual Selection")).toBeTruthy();
      });
      expect(screen.queryByDisplayValue("Ironhide Brute")).toBeNull();
    });

    it("blocks submit when description is missing", async () => {
      const user = userEvent.setup();
      const createSpy = vi.spyOn(liveApi, "createThreatDraft");
      render(<StatblockWorkbenchModule />);
      await user.click(screen.getByTestId("create-and-generate-submit"));
      await waitFor(() => {
        expect(screen.getByTestId("create-threat-error").textContent).toMatch(/description/i);
      });
      expect(createSpy).not.toHaveBeenCalled();
    });

    it("preserves form and reports uncertainty on create transport failure", async () => {
      const user = userEvent.setup();
      vi.spyOn(liveApi, "createThreatDraft").mockRejectedValue(new TypeError("Failed to fetch"));
      const generateSpy = vi.spyOn(liveApi, "generateThreatDraftCandidate");

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));

      await waitFor(() => {
        expect(screen.getByTestId("create-threat-error").textContent).toMatch(/outcome unknown/i);
      });
      expect(generateSpy).not.toHaveBeenCalled();
      expect(screen.getByTestId("create-threat-description")).toHaveProperty("value", THREAT_DESCRIPTION);
    });

    it("stores the draft/candidate join in sessionStorage and restores it on remount", async () => {
      const user = userEvent.setup();
      vi.spyOn(liveApi, "createThreatDraft").mockResolvedValue(mockCreatedDraft());
      vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
        schema: "dmb_generate_threat_draft_candidate_response_v1",
        draft_id: DRAFT_ID,
        generated_from_draft_version: 1,
        request_id: "req_join_persist",
        outcome: "success",
        candidate,
        cache_status: "stored",
        persistence_failures: [],
      });
      const getSpy = vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: DRAFT_ID,
        operation_id: "op_join_restore_accept",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_join",
          revision_id: "rev_join",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      const first = render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });

      const stored = JSON.parse(sessionStorage.getItem("dmb.sbw.workbenchJoin") ?? "null") as {
        draft_id?: string;
        candidate_id?: string;
        version?: number;
        name?: string;
      };
      expect(stored).toMatchObject({
        draft_id: DRAFT_ID,
        version: 1,
        candidate_id: "cand_fixture1",
        name: "Mireward Latchling",
      });

      first.unmount();
      getSpy.mockClear();
      const remountUser = userEvent.setup();
      render(<StatblockWorkbenchModule />);
      await waitFor(() => {
        expect(getSpy).toHaveBeenCalledWith("cand_fixture1");
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      expect(screen.getByPlaceholderText("td_…")).toHaveProperty("value", DRAFT_ID);

      await validateWorkingCopy(remountUser);
      expect(screen.getByTestId("workbench-edit-dock").textContent).not.toMatch(
        /ThreatDraft identity missing/i,
      );
      await remountUser.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(acceptSpy).toHaveBeenCalledTimes(1);
      });
      expect(acceptSpy.mock.calls[0][0]).toBe(DRAFT_ID);
      await waitFor(() => {
        expect(screen.getByText(/Mechanics saved; not published/i)).toBeTruthy();
      });
    });

    it("restores Accept draft identity from sessionStorage even when Advanced draft fields are empty", async () => {
      sessionStorage.setItem(
        "dmb.sbw.workbenchJoin",
        JSON.stringify({
          draft_id: DRAFT_ID,
          version: 1,
          name: "Mireward Latchling",
          candidate_id: "cand_fixture1",
        }),
      );
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: DRAFT_ID,
        operation_id: "op_storage_only_accept",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_storage",
          revision_id: "rev_storage",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      const user = userEvent.setup();
      render(<StatblockWorkbenchModule />);
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await validateWorkingCopy(user);
      expect(screen.getByTestId("workbench-edit-dock").textContent).toMatch(
        /Ready to Accept\/Save mechanics/i,
      );
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(acceptSpy).toHaveBeenCalledWith(
          DRAFT_ID,
          expect.objectContaining({ expected_draft_version: 1 }),
        );
      });
    });

    it("recovers ThreatDraft identity from candidate read source_draft fields", async () => {
      sessionStorage.setItem(
        "dmb.sbw.workbenchJoin",
        JSON.stringify({
          draft_id: null,
          version: null,
          name: null,
          candidate_id: "cand_fixture1",
        }),
      );
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue({
        ...activeResponse,
        source_draft_id: DRAFT_ID,
        source_draft_version: 1,
        source_draft_name: "Mireward Latchling",
      });
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockResolvedValue({
        schema: "dmb_accept_threat_draft_mechanics_response_v1",
        draft_id: DRAFT_ID,
        operation_id: "op_source_draft_recover",
        result_label: "mechanics_saved",
        locator: {
          provider: "dungeonmind",
          statblock_id: "sb_src",
          revision_id: "rev_src",
          contract: "dungeonbuddy-statblocks-v1",
          contract_version: "1",
          definition_digest: PREVIEW_DIGEST,
        },
      });

      const user = userEvent.setup();
      render(<StatblockWorkbenchModule />);
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      expect(screen.getByPlaceholderText("td_…")).toHaveProperty("value", DRAFT_ID);
      const stored = JSON.parse(sessionStorage.getItem("dmb.sbw.workbenchJoin") ?? "null");
      expect(stored).toMatchObject({
        draft_id: DRAFT_ID,
        version: 1,
        candidate_id: "cand_fixture1",
      });

      await validateWorkingCopy(user);
      expect(screen.getByTestId("workbench-edit-dock").textContent).not.toMatch(
        /ThreatDraft identity missing/i,
      );
      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      await waitFor(() => {
        expect(acceptSpy).toHaveBeenCalledWith(
          DRAFT_ID,
          expect.objectContaining({ expected_draft_version: 1 }),
        );
      });
    });

    it("clears the stored join when starting another threat", async () => {
      const user = userEvent.setup();
      vi.spyOn(liveApi, "createThreatDraft").mockResolvedValue(mockCreatedDraft());
      vi.spyOn(liveApi, "generateThreatDraftCandidate").mockResolvedValue({
        schema: "dmb_generate_threat_draft_candidate_response_v1",
        draft_id: DRAFT_ID,
        generated_from_draft_version: 1,
        request_id: "req_join_clear",
        outcome: "success",
        candidate,
        cache_status: "stored",
        persistence_failures: [],
      });
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);

      render(<StatblockWorkbenchModule />);
      await fillRequiredCreateFields(user);
      await user.click(screen.getByTestId("create-and-generate-submit"));
      await waitFor(() => {
        expect(sessionStorage.getItem("dmb.sbw.workbenchJoin")).toBeTruthy();
      });

      await user.click(screen.getByTestId("start-another-threat"));
      expect(sessionStorage.getItem("dmb.sbw.workbenchJoin")).toBeNull();
      expect(screen.queryByTestId("statblock-definition-editor")).toBeNull();
    });

    it("restores edited rule-element rules_text across remount from sessionStorage", async () => {
      const getSpy = vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      const user = userEvent.setup();
      const first = render(<StatblockWorkbenchModule />);
      await user.type(screen.getByPlaceholderText("cand_…"), "cand_fixture1");
      await user.click(screen.getByRole("button", { name: "Load candidate" }));
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });

      const rulesInput = screen.getByLabelText("Rule element rules text greatclub");
      await user.clear(rulesInput);
      await user.type(rulesInput, "Edited siege latch rules for dogfood.");

      await waitFor(() => {
        const stored = JSON.parse(sessionStorage.getItem("dmb.sbw.workbenchJoin") ?? "null") as {
          candidate_id?: string;
          working_copy?: { rule_elements?: Array<{ key: string; rules_text?: string }> };
        };
        expect(stored.candidate_id).toBe("cand_fixture1");
        const greatclub = stored.working_copy?.rule_elements?.find((el) => el.key === "greatclub");
        expect(greatclub?.rules_text).toBe("Edited siege latch rules for dogfood.");
      });

      first.unmount();
      getSpy.mockClear();
      render(<StatblockWorkbenchModule />);
      await waitFor(() => {
        expect(getSpy).toHaveBeenCalledWith("cand_fixture1");
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      expect(screen.getByLabelText("Rule element rules text greatclub")).toHaveProperty(
        "value",
        "Edited siege latch rules for dogfood.",
      );
    });
  });
});
