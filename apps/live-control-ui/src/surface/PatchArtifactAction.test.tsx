import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeCapabilityResponse, makeRollTableArtifact, makeWriteResult } from "../test/fixtures";
import { PatchArtifactAction } from "./PatchArtifactAction";

const capability = makeCapabilityResponse().capabilities.find(
  (candidate) => candidate.command_type === "patch_artifact",
)!;
const target = makeCapabilityResponse().target;

function makePreviewResult() {
  return makeWriteResult({
    status: "noop",
    diagnostics: ["dry-run preview generated"],
    metadata: {
      patch: {
        dry_run: true,
        source_path: "tables/storm_weather.md",
        file_state_token_before: "table-token-1",
        file_state_token_after: "table-token-preview",
        old_text_length: 8,
        new_text_length: 12,
        replacement_count: 1,
        unified_diff: "@@ -1,2 +1,2 @@\n-Calm skies\n+Heavy hail",
      },
    },
  });
}

describe("PatchArtifactAction", () => {
  it("blocks preview when old_text is empty", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makePreviewResult());
    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    expect(screen.getByRole("button", { name: "Preview patch" })).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("blocks preview when new_text is empty", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makePreviewResult());
    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    expect(screen.getByRole("button", { name: "Preview patch" })).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("blocks preview when old_text and new_text are identical", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makePreviewResult());
    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Calm skies");
    expect(screen.getByRole("button", { name: "Preview patch" })).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables patching when file_state_token is missing", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makePreviewResult());
    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact({ file_state_token: null })}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    expect(screen.getByText(/no file state token was returned/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview patch" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Confirm patch" })).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits preview as dry_run patch_artifact with expected payload shape", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makePreviewResult());
    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    await user.type(screen.getByLabelText("Rationale (optional)"), "Raise weather pressure");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const command = onSubmit.mock.calls[0][0];
    expect(command.command_type).toBe("patch_artifact");
    expect(command.lane).toBe("prep_note");
    expect(command.idempotency_key).toBeNull();
    expect(command.payload).toMatchObject({
      expected_file_state_token: "table-token-1",
      old_text: "Calm skies",
      new_text: "Heavy hail",
      rationale: "Raise weather pressure",
      dry_run: true,
    });
    expect(command.payload).not.toHaveProperty("source_path");
    expect(command.payload).not.toHaveProperty("file_path");
    expect(command.payload).not.toHaveProperty("path");
    expect(command.payload).not.toHaveProperty("artifact_text");
  });

  it("renders preview metadata and enables confirm only after successful preview", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makePreviewResult());
    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    expect(screen.getByRole("button", { name: "Confirm patch" })).toBeDisabled();

    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));

    expect(await screen.findByText(/Preview mode: server dry-run confirmed/i)).toBeInTheDocument();
    expect(screen.getByText("Before token: table-token-1")).toBeInTheDocument();
    expect(screen.getByText("After token: table-token-preview")).toBeInTheDocument();
    expect(screen.getByText("Replacement count: 1")).toBeInTheDocument();
    expect(screen.getByText(/@@ -1,2 \+1,2 @@/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm patch" })).toBeEnabled();
  });

  it("invalidates preview when editing fields after preview", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makePreviewResult());
    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));
    expect(screen.getByRole("button", { name: "Confirm patch" })).toBeEnabled();

    await user.type(screen.getByLabelText("Replacement text"), "!");
    expect(screen.getByRole("button", { name: "Confirm patch" })).toBeDisabled();
  });

  it("submits confirm as non-dry-run using previewed values and idempotency key", async () => {
    const user = userEvent.setup();
    const onSubmit = vi
      .fn()
      .mockResolvedValueOnce(makePreviewResult())
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "accepted",
          events_appended: ["evt-patch-1"],
          artifacts_changed: [target],
          metadata: {
            patch: {
              dry_run: false,
              file_state_token_before: "table-token-1",
              file_state_token_after: "table-token-2",
              replacement_count: 1,
            },
          },
        }),
      );
    const onAccepted = vi.fn(async () => undefined);
    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
        onAccepted={onAccepted}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));
    await user.click(screen.getByRole("button", { name: "Confirm patch" }));

    expect(onSubmit).toHaveBeenCalledTimes(2);
    const confirmCommand = onSubmit.mock.calls[1][0];
    expect(confirmCommand.payload).toMatchObject({
      expected_file_state_token: "table-token-1",
      old_text: "Calm skies",
      new_text: "Heavy hail",
      dry_run: false,
    });
    expect(typeof confirmCommand.idempotency_key).toBe("string");
    expect(confirmCommand.idempotency_key).toContain("ui-patch-artifact");
    expect(await screen.findByText("Patch applied.")).toBeInTheDocument();
    expect(screen.getByText("Audit event: evt-patch-1")).toBeInTheDocument();
    expect(screen.getByText("Artifact changed: roll_table T-WX")).toBeInTheDocument();
    expect(onAccepted).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Text to replace")).toHaveValue("");
    expect(screen.getByLabelText("Replacement text")).toHaveValue("");
  });

  it("shows conflict/rejected/noop diagnostics without claiming success", async () => {
    const user = userEvent.setup();
    const onSubmit = vi
      .fn()
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "conflict",
          conflicts: [
            {
              conflict_type: "stale_artifact",
              message: "artifact changed since last read",
              target,
              recoverable: true,
            },
          ],
          metadata: {},
        }),
      )
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "rejected",
          conflicts: [
            {
              conflict_type: "invalid_payload",
              message: "old_text must match exactly once",
              target,
              recoverable: true,
            },
          ],
          diagnostics: ["replacement_count=0"],
          metadata: {},
        }),
      )
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "noop",
          diagnostics: ["dry-run preview generated"],
          metadata: {
            patch: {
              dry_run: true,
            },
          },
        }),
      );

    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));
    expect(await screen.findByText(/stale_artifact: artifact changed since last read/)).toBeInTheDocument();
    expect(screen.queryByText("Patch applied.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Preview patch" }));
    expect(await screen.findByText(/invalid_payload: old_text must match exactly once/)).toBeInTheDocument();
    expect(screen.getByText(/replacement_count=0/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Preview patch" }));
    expect(await screen.findByText(/Preview mode: server dry-run confirmed/)).toBeInTheDocument();
  });

  it("reuses confirm idempotency key after confirm network error, but regenerates after new preview", async () => {
    const user = userEvent.setup();
    const onSubmit = vi
      .fn()
      .mockResolvedValueOnce(makePreviewResult())
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "accepted",
          metadata: {
            patch: {
              dry_run: false,
            },
          },
        }),
      )
      .mockResolvedValueOnce(makePreviewResult())
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "accepted",
          metadata: {
            patch: {
              dry_run: false,
            },
          },
        }),
      );

    render(
      <PatchArtifactAction
        target={target}
        capability={capability}
        artifact={makeRollTableArtifact()}
        onSubmitCommand={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));

    await user.click(screen.getByRole("button", { name: "Confirm patch" }));
    expect(await screen.findByText("network down")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirm patch" }));

    const failedConfirmKey = onSubmit.mock.calls[1][0].idempotency_key;
    const retriedConfirmKey = onSubmit.mock.calls[2][0].idempotency_key;
    expect(failedConfirmKey).toEqual(retriedConfirmKey);

    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail!");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));
    await user.click(screen.getByRole("button", { name: "Confirm patch" }));
    const nextPatchConfirmKey = onSubmit.mock.calls[4][0].idempotency_key;
    expect(nextPatchConfirmKey).not.toEqual(failedConfirmKey);
  });
});
