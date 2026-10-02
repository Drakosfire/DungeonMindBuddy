import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { baseCandidateDefinition, complexCandidateDefinition } from "./editorFixtures";
import { StatblockDefinitionEditor } from "./StatblockDefinitionEditor";
import {
  createEditorStateFromOutput,
  markValidationAssociated,
  setIdentityName,
  type StatblockEditorState,
} from "./statblockEditorState";

function ControlledEditor({ output }: { output: ReturnType<typeof baseCandidateDefinition> }) {
  const [state, setState] = useState<StatblockEditorState>(() => createEditorStateFromOutput(output));
  return <StatblockDefinitionEditor output={output} editorState={state} onEditorStateChange={setState} />;
}

function movementCandidateDefinition() {
  const output = baseCandidateDefinition();
  return {
    ...output,
    movement: {
      modes: [
        { key: "foot", mode: "walk" as const, distance: { value: 30, unit: "feet" as const }, qualifiers: ["land"] },
      ],
    },
    rule_elements: output.rule_elements.map((element, index) =>
      index === 0
        ? {
            ...element,
            key: "marsh_stride",
            mechanic: {
              kind: "composite" as const,
              target: null,
              effects: [
                {
                  kind: "movement" as const,
                  movement_mode_key: "swim",
                  distance: { value: 20, unit: "feet" as const },
                },
              ],
            },
          }
        : element,
    ),
  };
}

describe("StatblockDefinitionEditor", () => {
  it("discloses rule element summary and uses honest remainder badges behind advanced", () => {
    render(<ControlledEditor output={baseCandidateDefinition()} />);

    const advanced = screen.getByTestId("editor-advanced-structure");
    expect(advanced).toBeInstanceOf(HTMLDetailsElement);
    expect((advanced as HTMLDetailsElement).open).toBe(false);
    expect(screen.getByText(/Advanced — full data structure/i)).toBeTruthy();

    const summaryBlock = document.querySelector('[data-protected-path="rule_elements[0].summary"]');
    expect(summaryBlock).toBeTruthy();
    expect(advanced.contains(summaryBlock!)).toBe(true);
    expect(summaryBlock!.querySelector("pre")?.textContent).toContain("null");

    const structureBlock = document.querySelector('[data-protected-path="rule_elements[0].structure"]');
    expect(structureBlock!.querySelector("pre")?.textContent).toContain('"summary"');
    expect(structureBlock!.getAttribute("data-protected-mode")).toBe("remainder");
    expect(structureBlock!.textContent).toMatch(/name and rules_text editable above/i);

    const identityProtected = document.querySelector('[data-protected-path="identity.protected"]');
    expect(identityProtected!.getAttribute("data-protected-mode")).toBe("remainder");
    expect(identityProtected!.textContent).toMatch(/name editable above/i);
    expect(identityProtected!.textContent).not.toMatch(/not editable via dedicated controls/i);

    const defenses = document.querySelector('[data-protected-path="defenses"]');
    expect(defenses!.getAttribute("data-protected-mode")).toBe("remainder");
    expect(defenses!.textContent).toMatch(/primary AC value editable above/i);

    const fullyProtected = document.querySelector('[data-protected-path="movement"]');
    expect(fullyProtected).toBeNull();
    expect(screen.getByRole("region", { name: "Movement modes" })).toBeTruthy();
    expect(screen.getByLabelText("Movement mode key 0")).toBeTruthy();
  });

  it("renders protected regions queryable in the DOM with session disclosure", () => {
    render(<ControlledEditor output={complexCandidateDefinition()} />);
    const advanced = screen.getByTestId("editor-advanced-structure");
    const protectedRegions = document.querySelectorAll('[data-editor-region="protected"]');
    expect(protectedRegions.length).toBeGreaterThan(0);
    expect(document.querySelector('[data-protected-path="lair"]')).toBeTruthy();
    expect(document.querySelector('[data-protected-path="phases"]')).toBeTruthy();
    expect(advanced.contains(document.querySelector('[data-protected-path="lair"]')!)).toBe(true);
    expect(screen.getByText(/Session-only working copy/)).toBeTruthy();
    expect(screen.getByText(/unsaved/i)).toBeTruthy();
  });

  it("shows complete complex mechanic JSON including spell names and nested effects", () => {
    render(<ControlledEditor output={complexCandidateDefinition()} />);
    expect(document.querySelector('[data-protected-path="rule_elements[1].summary"] pre')?.textContent).toContain(
      "Innate casting",
    );
    const spellBlock = document.querySelector('[data-protected-path="rule_elements[1].mechanic"]');
    expect(spellBlock).toBeTruthy();
    const pre = spellBlock!.querySelector("pre");
    expect(pre?.textContent).toContain("Fear");
    expect(pre?.textContent).toContain("Fireball");
    expect(pre?.textContent).toContain("spellcasting");

    const lairPre = document.querySelector('[data-protected-path="lair"] pre');
    expect(lairPre?.textContent).toContain("Ironhold");

    const phasesPre = document.querySelector('[data-protected-path="phases"] pre');
    expect(phasesPre?.textContent).toContain("enraged");
    expect(phasesPre?.textContent).toContain("enabled_element_keys");
  });

  it("updates ui status when editing", async () => {
    const user = userEvent.setup();
    render(<ControlledEditor output={baseCandidateDefinition()} />);
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("clean_unvalidated");

    await user.clear(screen.getByLabelText("Creature name"));
    await user.type(screen.getByLabelText("Creature name"), "New Name");
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
  });

  it("preserves protected mechanic content when editing dedicated name field", async () => {
    const user = userEvent.setup();
    render(<ControlledEditor output={complexCandidateDefinition()} />);

    const spellBlock = document.querySelector('[data-protected-path="rule_elements[1].mechanic"]');
    const preBefore = spellBlock!.querySelector("pre")!.textContent;
    expect(preBefore).toContain("Fear");

    const nameInput = screen.getByLabelText("Rule element name innate_spellcasting");
    await user.clear(nameInput);
    await user.type(nameInput, "Renamed Casting");

    const preAfter = spellBlock!.querySelector("pre")!.textContent;
    expect(preAfter).toContain("Fear");
    expect(preAfter).toContain("Fireball");
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

  it("clears validation association through edit flow in controlled state", async () => {
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
    expect(latest.validatedRevision).toBeNull();
  });

  it("keeps movement keys and effect references independent while editing typed fields", async () => {
    const user = userEvent.setup();
    const output = movementCandidateDefinition();
    let latest = markValidationAssociated(
      createEditorStateFromOutput(output),
      "validated_with_warnings",
    );
    const untouchedElement = structuredClone(latest.workingCopy.rule_elements[1]);

    function Harness() {
      const [state, setState] = useState(latest);
      latest = state;
      return <StatblockDefinitionEditor output={output} editorState={state} onEditorStateChange={setState} />;
    }

    render(<Harness />);

    await user.selectOptions(screen.getByLabelText("Movement mode kind 0"), "swim");
    expect(latest.workingCopy.movement.modes[0]).toMatchObject({ key: "foot", mode: "swim" });
    expect(screen.getByLabelText("Movement mode reference marsh_stride 0")).toHaveProperty(
      "value",
      "swim",
    );

    const keyInput = screen.getByLabelText("Movement mode key 0");
    await user.clear(keyInput);
    await user.type(keyInput, "waterway");
    expect(screen.getByLabelText("Movement mode reference marsh_stride 0")).toHaveProperty(
      "value",
      "swim",
    );

    const referenceInput = screen.getByLabelText("Movement mode reference marsh_stride 0");
    await user.clear(referenceInput);
    await user.type(referenceInput, "waterway");
    await user.clear(screen.getByLabelText("Movement mode distance 0"));
    await user.type(screen.getByLabelText("Movement mode distance 0"), "45");
    await user.clear(screen.getByLabelText("Movement mode qualifier 0 0"));
    await user.type(screen.getByLabelText("Movement mode qualifier 0 0"), "submerged");

    expect(latest.workingCopy.movement.modes[0]).toEqual({
      key: "waterway",
      mode: "swim",
      distance: { value: 45, unit: "feet" },
      qualifiers: ["submerged"],
    });
    expect(latest.workingCopy.rule_elements[0].mechanic).toEqual({
      kind: "composite",
      target: null,
      effects: [
        {
          kind: "movement",
          movement_mode_key: "waterway",
          distance: { value: 20, unit: "feet" },
        },
      ],
    });
    expect(latest.workingCopy.rule_elements[1]).toEqual(untouchedElement);
    expect(latest.validatedRevision).toBeNull();
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("dirty_unvalidated");
  });

  it("adds a movement entry without inferring or rewriting its reference", async () => {
    const user = userEvent.setup();
    const output = movementCandidateDefinition();
    function Harness() {
      const [state, setState] = useState(() => createEditorStateFromOutput(output));
      return <StatblockDefinitionEditor output={output} editorState={state} onEditorStateChange={setState} />;
    }

    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "Add movement mode" }));
    await user.type(screen.getByLabelText("Movement mode key 1"), "waterway");
    await user.selectOptions(screen.getByLabelText("Movement mode kind 1"), "swim");
    await user.clear(screen.getByLabelText("Movement mode distance 1"));
    await user.type(screen.getByLabelText("Movement mode distance 1"), "25");
    await user.click(screen.getByRole("button", { name: "Add qualifier to movement mode 1" }));
    await user.type(screen.getByLabelText("Movement mode qualifier 1 0"), "submerged");

    expect(screen.getByLabelText("Movement mode reference marsh_stride 0")).toHaveProperty(
      "value",
      "swim",
    );
    await user.clear(screen.getByLabelText("Movement mode reference marsh_stride 0"));
    await user.type(screen.getByLabelText("Movement mode reference marsh_stride 0"), "waterway");

    expect(screen.getByLabelText("Movement mode key 1")).toHaveProperty("value", "waterway");
    expect(screen.getByLabelText("Movement mode kind 1")).toHaveProperty("value", "swim");
  });

  it("shows validated status while dirty when validation is associated at current revision", () => {
    const output = baseCandidateDefinition();
    let state = setIdentityName(createEditorStateFromOutput(output), "Dirty name");
    state = markValidationAssociated(state, "validated_with_warnings");

    render(<StatblockDefinitionEditor output={output} editorState={state} onEditorStateChange={() => undefined} />);
    expect(screen.getByTestId("editor-ui-status").textContent).toContain("validated_with_warnings");
  });

  it("leaves unrelated definition subtrees untouched after name and rules_text edits", async () => {
    const user = userEvent.setup();
    const output = complexCandidateDefinition();
    const beforeSpellMechanic = structuredClone(
      createEditorStateFromOutput(output).workingCopy.rule_elements.find(
        (element) => element.key === "innate_spellcasting",
      )!.mechanic,
    );

    function Harness() {
      const [state, setState] = useState(() => createEditorStateFromOutput(output));
      return <StatblockDefinitionEditor output={output} editorState={state} onEditorStateChange={setState} />;
    }

    render(<Harness />);

    const mechanicPre = () =>
      document.querySelector('[data-protected-path="rule_elements[1].mechanic"] pre')?.textContent ?? "";

    expect(mechanicPre()).toContain("Fear");
    const mechanicBeforeEdits = mechanicPre();

    await user.clear(screen.getByLabelText("Creature name"));
    await user.type(screen.getByLabelText("Creature name"), "Edited creature");

    const rulesInput = screen.getByLabelText("Rule element rules text innate_spellcasting");
    await user.clear(rulesInput);
    await user.type(rulesInput, "New rules body");

    expect((rulesInput as HTMLTextAreaElement).value).toBe("New rules body");
    expect(mechanicPre()).toBe(mechanicBeforeEdits);
    expect(JSON.parse(mechanicPre()!)).toEqual(beforeSpellMechanic);
  });
});
