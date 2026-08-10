import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PlanDocumentCreateControl } from "./PlanDocumentCreateControl";

const baseProps = {
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  suggestedSession: 23,
  suggestedTitle: "C2 Session 23 Prep",
  onSubmit: vi.fn(),
};

describe("PlanDocumentCreateControl", () => {
  it("opens an inline form with suggested defaults and For session label", async () => {
    const user = userEvent.setup();
    render(<PlanDocumentCreateControl {...baseProps} />);

    await user.click(screen.getByTestId("plan-document-create-open"));

    expect(screen.getByText("For session")).toBeInTheDocument();
    expect(screen.getByTestId("plan-document-create-session")).toHaveValue(23);
    expect(screen.getByTestId("plan-document-create-title")).toHaveValue("C2 Session 23 Prep");
  });

  it("does not overwrite a manually edited title when session changes", async () => {
    const user = userEvent.setup();
    render(<PlanDocumentCreateControl {...baseProps} />);

    await user.click(screen.getByTestId("plan-document-create-open"));
    const titleInput = screen.getByTestId("plan-document-create-title");
    await user.clear(titleInput);
    await user.type(titleInput, "Custom prep title");

    const sessionInput = screen.getByTestId("plan-document-create-session");
    await user.clear(sessionInput);
    await user.type(sessionInput, "26");

    expect(titleInput).toHaveValue("Custom prep title");
  });

  it("updates the title when session changes before manual title edit", async () => {
    const user = userEvent.setup();
    render(<PlanDocumentCreateControl {...baseProps} />);

    await user.click(screen.getByTestId("plan-document-create-open"));
    fireEvent.change(screen.getByTestId("plan-document-create-session"), {
      target: { value: "26" },
    });

    expect(screen.getByTestId("plan-document-create-title")).toHaveValue("C2 Session 26 Prep");
  });

  it("allows create for campaigns without a derivable corpus Session Prep path", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(
      <PlanDocumentCreateControl
        {...baseProps}
        campaignId="unknown-campaign"
        suggestedSession={5}
        suggestedTitle="Session 5 sketch"
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByTestId("plan-document-create-open"));
    expect(screen.queryByTestId("plan-document-create-path-error")).not.toBeInTheDocument();
    expect(screen.getByTestId("plan-document-create-submit")).not.toBeDisabled();
    await user.click(screen.getByTestId("plan-document-create-submit"));
    expect(onSubmit).toHaveBeenCalledWith({
      title: "Session 5 sketch",
      targetSession: 5,
    });
  });

  it("shows same-session helper and blocks duplicate titles among active same-session docs", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(
      <PlanDocumentCreateControl
        {...baseProps}
        suggestedSession={27}
        suggestedTitle="C2 Session 27 Prep"
        activeDocuments={[
          { title: "C2 Session 27 Prep", targetSession: 27 },
          { title: "If the party goes north", targetSession: 27 },
          { title: "Older discarded reuse ok", targetSession: 26 },
        ]}
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByTestId("plan-document-create-open"));
    expect(screen.getByTestId("plan-document-create-same-session")).toHaveTextContent(
      "2 other preps are already aimed at Session 27",
    );
    expect(screen.getByTestId("plan-document-create-title-error")).toBeInTheDocument();
    expect(screen.getByTestId("plan-document-create-submit")).toBeDisabled();

    const titleInput = screen.getByTestId("plan-document-create-title");
    await user.clear(titleInput);
    await user.type(titleInput, "If the siege breaks");
    expect(screen.queryByTestId("plan-document-create-title-error")).not.toBeInTheDocument();
    await user.click(screen.getByTestId("plan-document-create-submit"));
    expect(onSubmit).toHaveBeenCalledWith({
      title: "If the siege breaks",
      targetSession: 27,
    });
  });

  it("submits title and target session", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PlanDocumentCreateControl {...baseProps} onSubmit={onSubmit} />);

    await user.click(screen.getByTestId("plan-document-create-open"));
    await user.click(screen.getByTestId("plan-document-create-submit"));

    expect(onSubmit).toHaveBeenCalledWith({
      title: "C2 Session 23 Prep",
      targetSession: 23,
    });
  });

  it("shows create and activation errors with retry open", async () => {
    const onRetryOpen = vi.fn();
    render(
      <PlanDocumentCreateControl
        {...baseProps}
        createError="Registry unavailable"
        activationError="Resolve failed"
        onRetryOpen={onRetryOpen}
      />,
    );

    expect(screen.getByTestId("plan-document-create-error")).toHaveTextContent(
      "Registry unavailable",
    );
    expect(screen.getByTestId("plan-document-create-activation-error")).toHaveTextContent(
      "Created but could not open",
    );

    const user = userEvent.setup();
    await user.click(screen.getByTestId("plan-document-create-retry-open"));
    expect(onRetryOpen).toHaveBeenCalled();
  });
});
