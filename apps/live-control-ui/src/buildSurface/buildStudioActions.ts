/** Build-local intents; they confer no document or Graph write authority. */
export const BUILD_STUDIO_ACTION = "dmb:build-studio-action";
export type BuildStudioAction = "new" | "import" | "open";
export function requestBuildStudioAction(action: BuildStudioAction) {
  window.dispatchEvent(new CustomEvent(BUILD_STUDIO_ACTION, { detail: action }));
}
export const buildStarterKey = (documentId: string) => `dmb.build.starter.${documentId}`;
export const BUILD_STARTER_CONTENT = [
  { type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "Start with a spark" }] },
  { type: "paragraph", content: [{ type: "text", text: "A place, a person, a strange rumor. What makes this corner of your world worth exploring?" }] },
  { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "The place" }] },
  { type: "paragraph", content: [{ type: "text", text: "What do we see, hear, and feel when we arrive?" }] },
  { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "The people" }] },
  { type: "paragraph", content: [{ type: "text", text: "Who belongs here? What do they want, and who stands in their way?" }] },
  { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "The unexpected" }] },
  { type: "paragraph", content: [{ type: "text", text: "A secret, a tension, or a choice that could change everything." }] },
];
