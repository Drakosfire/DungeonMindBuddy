import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DurableSaveStatus } from "./DurableSaveStatus";

describe("DurableSaveStatus", () => {
  it("presents a durable saved timestamp as a machine-readable time", () => {
    render(<DurableSaveStatus state="saved" savedAt="2026-10-18T16:30:00Z" />);

    expect(screen.getByText("Saved")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.tagName === "TIME")).toHaveAttribute(
      "dateTime",
      "2026-10-18T16:30:00.000Z",
    );
  });

  it("never labels a missing or invalid timestamp as saved", () => {
    const { rerender } = render(<DurableSaveStatus state="saved" savedAt={null} />);
    expect(screen.getByRole("status")).toHaveTextContent("Saved time unavailable");

    rerender(<DurableSaveStatus state="saved" savedAt="not-a-server-time" />);
    expect(screen.queryByText("Saved", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByRole("time")).not.toBeInTheDocument();
  });

  it("keeps the last durable time distinct from unsaved edits", () => {
    render(<DurableSaveStatus state="unsaved" savedAt="2026-10-18T16:30:00Z" />);

    expect(screen.getByRole("status")).toHaveTextContent("Unsaved changes");
    expect(screen.getByRole("time")).toHaveTextContent("Last saved");
  });
});
