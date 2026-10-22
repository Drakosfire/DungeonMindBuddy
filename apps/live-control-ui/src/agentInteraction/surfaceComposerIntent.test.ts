import { describe, expect, it } from "vitest";
import { classifySurfaceComposerIntent } from "./surfaceComposerIntent";

describe("image artifacts versus surface edits", () => {
  it.each([
    "Write that as an image prompt and lets generate one",
    "Write an image prompt for the boardwalk.",
    "Please draft a prompt for an image of a forest.",
    "Could you please prepare a prompt to generate an illustration?",
    "Turn this into an image prompt.",
    "Make an image of the swamp.",
    "Generate an image of this scene.",
    "Edit the image prompt.",
    "Rewrite the image prompt using the Plan for context.",
    "Write an image prompt for this scene.",
    "Write an image prompt, but do not insert it into the Plan.",
    "Write an image prompt and don't insert anything into the Plan.",
  ])("prepares an artifact without a surface edit: %s", message => {
    expect(classifySurfaceComposerIntent(message)).toBe("discuss");
  });

  it.each([
    "Write a scene describing an image of a forest.",
    "Add a paragraph describing the image to this scene.",
    "Write an image prompt in the selected card.",
    "Rewrite the image prompt in this scene.",
    "Prepare an image and insert it into the Plan.",
    "Generate an image of the swamp, then replace the selected scene with it.",
    "Write an image prompt; append it to this page.",
    "Write an image prompt at the editor cursor.",
    "Make an image prompt and edit the current Plan.",
  ])("preserves explicit surface mutation preview: %s", message => {
    expect(classifySurfaceComposerIntent(message)).toBe("propose");
  });
});
