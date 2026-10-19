import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PlanCardDeck } from "./PlanCardDeck";
import type { WorldPlanCardNode } from "./WorldPlanCardProjection";

vi.mock("../../media/useSavedMediaImage", () => ({ useSavedMediaImage: () => ({ url: "https://imagedelivery.net/fixture/map", onError: vi.fn() }) }));
afterEach(() => vi.unstubAllGlobals());
const scene: WorldPlanCardNode = {
  kind: "scene", id: "scene:harbor", title: "Harbor", titleContent: [], order: 1,
  parentId: "beat:arrival", children: [], bodyText: "", bodyContent: [
    { type: "paragraph", content: [{ type: "text", text: "An authored <script> lantern cue." }] },
    { type: "paragraph", content: [{ type: "mediaImage", attrs: { assetId: "ac6c15cc-8c68-4732-8ae2-d9f3f051393a", alt: "Harbor map" } }] },
  ],
};

it("shows an inert draft thumbnail with saved media and keeps the full scene target", () => {
  const select = vi.fn();
  const { rerender } = render(<PlanCardDeck scenes={[scene]} nodes={[scene]} sceneId={scene.id} onSelect={select} visible />);
  const card = screen.getByRole("button", { name: "Show scene: Harbor" });
  expect(card).toHaveAttribute("aria-current", "true");
  expect(card).toHaveTextContent("An authored <script> lantern cue.");
  expect(card.querySelector("script")).toBeNull();
  expect(card.querySelectorAll("button, a, input, textarea")).toHaveLength(0);
  expect(card.querySelector("img")).toHaveAttribute("src", "https://imagedelivery.net/fixture/map");
  fireEvent.click(card);
  expect(select).toHaveBeenCalledWith("scene:harbor");
  rerender(<PlanCardDeck scenes={[{ ...scene, bodyContent: [{ type: "paragraph", content: [{ type: "text", text: "New unsaved harbor cue" }] }] }]} nodes={[scene]} sceneId={scene.id} onSelect={select} visible />);
  expect(card).toHaveTextContent("New unsaved harbor cue");
  expect(select).toHaveBeenCalledTimes(1);
});

it("starts collapsed on narrow screens and returns focus to its toggle after selection", () => {
  vi.stubGlobal("matchMedia", () => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  const select = vi.fn();
  render(<PlanCardDeck scenes={[scene]} nodes={[scene]} sceneId={null} onSelect={select} visible />);
  const deck = screen.getByRole("navigation", { name: "Contents" });
  const toggle = within(deck).getByRole("button", { name: /Contents · 1/ });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(within(deck).queryByRole("button", { name: "Show scene: Harbor" })).toBeNull();
  fireEvent.click(toggle);
  fireEvent.click(within(deck).getByRole("button", { name: "Show scene: Harbor" }));
  expect(select).toHaveBeenCalledWith("scene:harbor");
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(toggle).toHaveFocus();
});
