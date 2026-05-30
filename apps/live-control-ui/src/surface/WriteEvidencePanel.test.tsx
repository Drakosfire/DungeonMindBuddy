import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeWriteResult } from "../test/fixtures";
import { WriteEvidencePanel } from "./WriteEvidencePanel";

describe("WriteEvidencePanel", () => {
  it("renders accepted evidence with audit events and changed artifacts", () => {
    const result = makeWriteResult({
      status: "accepted",
      events_appended: ["evt-patch-123"],
      artifacts_changed: [
        {
          target_type: "roll_table",
          target_id: "T-WX",
          label: "Storm weather",
          source_status: "authoritative",
          metadata: {},
        },
      ],
      metadata: {
        patch: {
          file_state_token_before: "before-token",
          file_state_token_after: "after-token",
          replacement_count: 1,
        },
      },
    });

    render(
      <WriteEvidencePanel
        result={result}
        refreshedArtifactToken="after-token"
        refreshError={null}
      />,
    );

    expect(screen.getByText("Patch accepted.")).toBeInTheDocument();
    expect(screen.getByText("Audit event: evt-patch-123")).toBeInTheDocument();
    expect(screen.getByText("Changed artifact: roll_table T-WX")).toBeInTheDocument();
    expect(screen.getByText("Before token: before-token")).toBeInTheDocument();
    expect(screen.getByText("After token: after-token")).toBeInTheDocument();
    expect(screen.getByText("Refreshed token: after-token")).toBeInTheDocument();
    expect(
      screen.getByText("Verified: refreshed artifact matches patched state."),
    ).toBeInTheDocument();
  });

  it("shows token mismatch warning when refreshed token differs", () => {
    const result = makeWriteResult({
      status: "accepted",
      metadata: {
        patch: {
          file_state_token_after: "after-token",
        },
      },
    });
    render(
      <WriteEvidencePanel
        result={result}
        refreshedArtifactToken="different-token"
        refreshError={null}
      />,
    );
    expect(
      screen.getByText(
        "Patch accepted, but refreshed artifact token did not match the write result. Refresh again before making another patch.",
      ),
    ).toBeInTheDocument();
  });

  it("shows accepted-refresh-failed message without claiming patch failure", () => {
    const result = makeWriteResult({
      status: "accepted",
      events_appended: ["evt-patch-1"],
    });
    render(
      <WriteEvidencePanel
        result={result}
        refreshedArtifactToken={null}
        refreshError="network timeout"
      />,
    );
    expect(
      screen.getByText(
        "Patch accepted, but refresh failed. The patch command returned accepted. Refresh the pane before making another patch.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Refresh error: network timeout")).toBeInTheDocument();
  });

  it("does not render full artifact content", () => {
    const result = makeWriteResult({
      status: "accepted",
      metadata: {
        patch: {
          source_path: "tables/storm_weather.md",
        },
      },
    });
    render(<WriteEvidencePanel result={result} refreshedArtifactToken={null} refreshError={null} />);
    expect(screen.getByText("Source path: tables/storm_weather.md")).toBeInTheDocument();
    expect(screen.queryByText(/## 1-4/)).not.toBeInTheDocument();
  });
});
