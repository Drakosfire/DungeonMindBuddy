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
    await user.tab();

    expect(titleInput).toHaveValue("Custom prep title");
  });

  it("updates the title when session changes before manual title edit", async () => {
    const user = userEvent.setup();
    render(<PlanDocumentCreateControl {...baseProps} />);

    await user.click(screen.getByTestId("plan-document-create-open"));
    const sessionInput = screen.getByTestId("plan-document-create-session");
    fireEvent.change(sessionInput, {
      target: { value: "26" },
    });
    fireEvent.blur(sessionInput);

    expect(screen.getByTestId("plan-document-create-title")).toHaveValue("C2 Session 26 Prep");
  });

  it("does not retarget helpers while session digits are mid-edit", async () => {
    const user = userEvent.setup();
    render(
      <PlanDocumentCreateControl
        {...baseProps}
        suggestedSession={27}
        suggestedTitle="C2 Session 27 Prep"
        activeDocuments={[
          { title: "C2 Session 27 Prep", targetSession: 27 },
          { title: "Lone Session 2", targetSession: 2 },
        ]}
      />,
    );

    await user.click(screen.getByTestId("plan-document-create-open"));
    expect(screen.getByTestId("plan-document-create-same-session")).toHaveTextContent(
      "1 other prep is already aimed at Session 27",
    );

    const sessionInput = screen.getByTestId("plan-document-create-session");
    fireEvent.change(sessionInput, { target: { value: "2" } });
    expect(screen.getByTestId("plan-document-create-same-session")).toHaveTextContent(
      "Session 27",
    );
    expect(screen.getByTestId("plan-document-create-title")).toHaveValue("C2 Session 27 Prep");

    fireEvent.change(sessionInput, { target: { value: "26" } });
    fireEvent.blur(sessionInput);
    expect(screen.getByTestId("plan-document-create-session")).toHaveValue(26);
    expect(screen.getByTestId("plan-document-create-title")).toHaveValue("C2 Session 26 Prep");
    expect(screen.getByTestId("plan-document-create-same-session")).not.toBeVisible();
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
    expect(screen.getByTestId("plan-document-create-title-error")).toHaveTextContent(
      'Another active prep for Session 27 is already titled "C2 Session 27 Prep"',
    );
    expect(screen.getByTestId("plan-document-create-title-error")).toHaveTextContent(
      'Choose a different name, such as "If the siege breaks"',
    );
    expect(screen.getByTestId("plan-document-create-submit")).toBeDisabled();

    const titleInput = screen.getByTestId("plan-document-create-title");
    await user.clear(titleInput);
    await user.type(titleInput, "If the party goes north");
    expect(screen.getByTestId("plan-document-create-title-error")).toHaveTextContent(
      'already titled "If the party goes north"',
    );

    await user.clear(titleInput);
    await user.type(titleInput, "If the siege breaks");
    expect(screen.getByTestId("plan-document-create-title-error")).not.toBeVisible();
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

  it("closes the form after a successful create cycle", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<PlanDocumentCreateControl {...baseProps} />);
    await user.click(screen.getByTestId("plan-document-create-open"));
    expect(screen.getByTestId("plan-document-create-form")).toBeInTheDocument();

    rerender(<PlanDocumentCreateControl {...baseProps} creating />);
    rerender(<PlanDocumentCreateControl {...baseProps} creating={false} />);
    expect(screen.queryByTestId("plan-document-create-form")).not.toBeInTheDocument();
    expect(screen.getByTestId("plan-document-create-open")).toBeInTheDocument();
  });

  it("keeps the form open when create fails", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<PlanDocumentCreateControl {...baseProps} />);
    await user.click(screen.getByTestId("plan-document-create-open"));

    rerender(<PlanDocumentCreateControl {...baseProps} creating />);
    rerender(
      <PlanDocumentCreateControl
        {...baseProps}
        creating={false}
        createError="Registry unavailable"
      />,
    );
    expect(screen.getByTestId("plan-document-create-form")).toBeInTheDocument();
    expect(screen.getByTestId("plan-document-create-error")).toHaveTextContent(
      "Registry unavailable",
    );
  });
});
