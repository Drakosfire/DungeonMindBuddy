import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { baseCandidateDefinition, complexCandidateDefinition } from "./editorFixtures";
import { StatblockDefinitionEditor } from "./StatblockDefinitionEditor";
import {
  createEditorStateFromOutput,
  markValidationAssociated,
  type StatblockEditorState,
} from "./statblockEditorState";

function ControlledEditor({ output }: { output: ReturnType<typeof baseCandidateDefinition> }) {
  const [state, setState] = useState<StatblockEditorState>(() => createEditorStateFromOutput(output));
  return <StatblockDefinitionEditor output={output} editorState={state} onEditorStateChange={setState} />;
}

describe("StatblockDefinitionEditor", () => {
  it("renders protected regions queryable in the DOM", () => {
    render(<ControlledEditor output={complexCandidateDefinition()} />);
    const protectedRegions = document.querySelectorAll('[data-editor-region="protected"]');
    expect(protectedRegions.length).toBeGreaterThan(0);
    expect(document.querySelector('[data-protected-path="lair"]')).toBeTruthy();
    expect(document.querySelector('[data-protected-path="phases"]')).toBeTruthy();
    expect(screen.getByText(/Session-only working copy/)).toBeTruthy();
  });

  it("updates ui status when editing", async () => {
    const user = userEvent.setup();
    render(<ControlledEditor output={baseCandidateDefinition()} />);
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("clean_unvalidated");

    await user.clear(screen.getByLabelText("Creature name"));
    await user.type(screen.getByLabelText("Creature name"), "New Name");
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
  });

  it("does not persist editor state to web storage", async () => {
    const localSpy = vi.spyOn(Storage.prototype, "setItem");
    const sessionSpy = vi.spyOn(sessionStorage, "setItem");

    render(<ControlledEditor output={baseCandidateDefinition()} />);
    await userEvent.type(screen.getByLabelText("Creature name"), "X");

    expect(localSpy).not.toHaveBeenCalled();
    expect(sessionSpy).not.toHaveBeenCalled();

    localSpy.mockRestore();
    sessionSpy.mockRestore();
  });

  it("clears validation eligibility through edit flow in controlled state", async () => {
    const user = userEvent.setup();
    const output = baseCandidateDefinition();
    let latest = markValidationAssociated(createEditorStateFromOutput(output), "validated_with_warnings");

    const Harness = () => {
      const [state, setState] = useState(latest);
      latest = state;
      return <StatblockDefinitionEditor output={output} editorState={state} onEditorStateChange={setState} />;
    };

    render(<Harness />);
    await user.type(screen.getByLabelText("Creature name"), "!");
    expect(latest.validationEligibility).toBe("unvalidated");
  });
});
