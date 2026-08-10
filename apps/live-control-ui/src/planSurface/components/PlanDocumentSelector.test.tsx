import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  fixturePlanDocumentDescriptor,
  fixtureWorkspaceDocumentRecord,
} from "../config/planSessionDescriptor";
import { PlanDocumentSelector } from "./PlanDocumentSelector";

const DOC_A = "11111111-1111-4111-8111-111111111111";
const DOC_B = "22222222-2222-4222-8222-222222222222";
const DOC_C = "33333333-3333-4333-8333-333333333333";

function renderSelector(overrides: Partial<Parameters<typeof PlanDocumentSelector>[0]> = {}) {
  const onSelect = vi.fn();
  const onRetryList = vi.fn();
  render(
    <PlanDocumentSelector
      documents={[
        fixtureWorkspaceDocumentRecord({ document_id: DOC_A, title: "C2 Session 23 Prep", target_session: 23 }),
        fixtureWorkspaceDocumentRecord({ document_id: DOC_B, title: "C2 Session 26 Prep", target_session: 26 }),
      ]}
      listStatus="ready"
      activeDocument={fixturePlanDocumentDescriptor({ documentId: DOC_A, title: "C2 Session 23 Prep" })}
      switching={false}
      switchError={null}
      onSelect={onSelect}
      onRetryList={onRetryList}
      {...overrides}
    />,
  );
  return { onSelect, onRetryList };
}

describe("PlanDocumentSelector", () => {
  it("labels the control as a prep document picker, not session/graph memory", () => {
    renderSelector();
    expect(screen.getByText("Prep document")).toBeInTheDocument();
    expect(screen.getByLabelText("Prep document")).toBe(screen.getByTestId("plan-document-select"));
  });

  it("keeps exact documentId identity on every option", () => {
    renderSelector();
    const select = screen.getByTestId("plan-document-select") as HTMLSelectElement;
    const values = Array.from(select.options).map((option) => option.value);
    expect(values).toEqual([DOC_A, DOC_B]);
    expect(select.value).toBe(DOC_A);
  });

  it("shows target session as presentation metadata, never as the option value", () => {
    renderSelector();
    const select = screen.getByTestId("plan-document-select") as HTMLSelectElement;
    const labels = Array.from(select.options).map((option) => option.textContent);
    expect(labels).toEqual(["C2 Session 23 Prep", "C2 Session 26 Prep"]);
    expect(select.options[1]?.value).toBe(DOC_B);
  });

  it("keeps duplicate titles as distinct options keyed by documentId", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderSelector({
      documents: [
        fixtureWorkspaceDocumentRecord({ document_id: DOC_A, title: "Gate contingency", target_session: 25 }),
        fixtureWorkspaceDocumentRecord({ document_id: DOC_B, title: "Gate contingency", target_session: 26 }),
      ],
      activeDocument: fixturePlanDocumentDescriptor({ documentId: DOC_A, title: "Gate contingency" }),
    });
    const select = screen.getByTestId("plan-document-select") as HTMLSelectElement;
    expect(select.options).toHaveLength(2);
    expect(select.options[0]?.value).toBe(DOC_A);
    expect(select.options[1]?.value).toBe(DOC_B);

    await user.selectOptions(select, DOC_B);
    expect(onSelect).toHaveBeenCalledWith(DOC_B);
    expect(onSelect).not.toHaveBeenCalledWith("Gate contingency");
  });

  it("marks the active document truthfully when the refreshed list no longer lists it", () => {
    renderSelector({
      documents: [
        fixtureWorkspaceDocumentRecord({ document_id: DOC_B, title: "C2 Session 26 Prep", target_session: 26 }),
      ],
      activeDocument: fixturePlanDocumentDescriptor({ documentId: DOC_A, title: "C2 Session 23 Prep" }),
    });
    const select = screen.getByTestId("plan-document-select") as HTMLSelectElement;
    expect(select.value).toBe(DOC_A);
    expect(select.options[0]?.textContent).toBe("C2 Session 23 Prep (no longer listed as active)");
  });

  it("stays enabled while switching so a newer choice can supersede a pending one", () => {
    renderSelector({ switching: true });
    expect(screen.getByTestId("plan-document-select")).not.toBeDisabled();
    expect(screen.getByTestId("plan-document-switching")).toHaveTextContent("Switching…");
  });

  it("surfaces a failed switch as an actionable alert without hiding the active document", () => {
    renderSelector({ switchError: "Could not open the selected prep document." });
    expect(screen.getByTestId("plan-document-switch-error")).toHaveTextContent(
      "Could not open the selected prep document.",
    );
    const select = screen.getByTestId("plan-document-select") as HTMLSelectElement;
    expect(select.value).toBe(DOC_A);
  });

  it("keeps the active document visible while the list is loading", () => {
    renderSelector({ documents: null, listStatus: "loading" });
    const select = screen.getByTestId("plan-document-select") as HTMLSelectElement;
    expect(select).toBeDisabled();
    expect(select.value).toBe(DOC_A);
    expect(screen.getByText("Loading documents…")).toBeInTheDocument();
  });

  it("offers retry when the list is unavailable without touching the active document", async () => {
    const user = userEvent.setup();
    const { onRetryList } = renderSelector({ documents: null, listStatus: "error" });
    const select = screen.getByTestId("plan-document-select") as HTMLSelectElement;
    expect(select).toBeDisabled();
    expect(select.value).toBe(DOC_A);
    expect(screen.getByRole("alert")).toHaveTextContent("Document list unavailable.");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetryList).toHaveBeenCalledTimes(1);
  });

  it("emits the exact selected documentId", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderSelector();
    await user.selectOptions(screen.getByTestId("plan-document-select"), DOC_B);
    expect(onSelect).toHaveBeenCalledWith(DOC_B);
  });
});
