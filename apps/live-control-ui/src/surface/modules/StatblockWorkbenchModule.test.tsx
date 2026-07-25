import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type {
  ReadStatblockCandidateResponseV1,
  GenerateThreatDraftCandidateResponseV1,
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
    expect(screen.queryByRole("button", { name: /accept/i })).toBeNull();
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
    expect(screen.queryByRole("button", { name: /Accept\/Save mechanics/i })).toBeNull();
  });

  describe("accept/save mechanics (SBW07c)", () => {
    it("shows Accept/Save after valid preview and confirms with stable operation_id", async () => {
      vi.spyOn(liveApi, "getStatblockCandidate").mockResolvedValue(activeResponse);
      vi.spyOn(liveApi, "validateStatblockDefinition").mockResolvedValue(successValidate("valid"));
      const acceptSpy = vi.spyOn(liveApi, "acceptThreatDraftMechanics").mockImplementation(
        () =>
          new Promise(() => {
            /* hang for double-click */
          }),
      );
      vi.spyOn(crypto, "randomUUID").mockReturnValue("11111111-2222-4333-8444-555555555555");

      const user = await loadId("cand_fixture1");
      await waitFor(() => {
        expect(screen.getByTestId("statblock-definition-editor")).toBeTruthy();
      });
      await user.type(screen.getByPlaceholderText("td_…"), "td_accept1");
      await validateWorkingCopy(user);

      expect(screen.getByRole("button", { name: "Accept/Save mechanics" })).toBeTruthy();

      await user.click(screen.getByRole("button", { name: "Accept/Save mechanics" }));
      const panel = screen.getByTestId("accept-mechanics-panel");
      expect(panel.textContent).toMatch(PREVIEW_DIGEST);
      expect(panel.textContent).toMatch(/not published to the World Graph/i);
      expect(panel.textContent).toMatch(/valid/);

      const confirm = screen.getByTestId("accept-mechanics-confirm");
      await user.click(confirm);
      await user.click(confirm);

      await waitFor(() => {
        expect(acceptSpy).toHaveBeenCalledTimes(2);
      });
      expect(acceptSpy.mock.calls[0][1].operation_id).toBe(
        "11111111-2222-4333-8444-555555555555",
      );
      expect(acceptSpy.mock.calls[1][1].operation_id).toBe(
        "11111111-2222-4333-8444-555555555555",
      );
      expect(acceptSpy.mock.calls[0][0]).toBe("td_accept1");
      expect(acceptSpy.mock.calls[0][1].expected_draft_version).toBe(1);
      expect(acceptSpy.mock.calls[0][1].validation_definition_digest).toBe(PREVIEW_DIGEST);
      expect(acceptSpy.mock.calls[0][1].source_candidate_id).toBe("cand_fixture1");
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
      await user.click(screen.getByTestId("accept-mechanics-confirm"));

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
      await user.click(screen.getByTestId("accept-mechanics-confirm"));

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
      await user.click(screen.getByTestId("accept-mechanics-confirm"));

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
      expect(screen.queryByRole("button", { name: "Accept/Save mechanics" })).toBeNull();
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
      expect(screen.queryByRole("button", { name: "Accept/Save mechanics" })).toBeNull();
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
      expect(screen.queryByRole("button", { name: "Accept/Save mechanics" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Reconcile acceptance" })).toBeNull();
      expect(uuidSpy).not.toHaveBeenCalled();
      expect(acceptSpy).not.toHaveBeenCalled();
    });
  });
});
