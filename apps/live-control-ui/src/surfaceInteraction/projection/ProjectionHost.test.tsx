import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectionHost } from "./ProjectionHost";
import type { ActiveProjection } from "./types";

const navigationItems = [
  { id: "recap", label: "Recap" },
  { id: "party-registry", label: "Party Registry" },
];

function renderHost(
  overrides: Partial<Parameters<typeof ProjectionHost>[0]> = {},
) {
  const onNavigate = vi.fn();
  const onToggle = vi.fn();
  const onClose = vi.fn();
  const onExpand = vi.fn();

  const result = render(
    <ProjectionHost
      active={null}
      navigationItems={navigationItems}
      labels={{}}
      body={null}
      onNavigate={onNavigate}
      onToggle={onToggle}
      onClose={onClose}
      onExpand={onExpand}
      {...overrides}
    />,
  );

  return { ...result, onNavigate, onToggle, onClose, onExpand };
}

describe("ProjectionHost shell", () => {
  beforeEach(() => {
    document.body.classList.remove("surface-projection-open");
  });

  afterEach(() => {
    document.body.classList.remove("surface-projection-open");
  });

  it("toggles open via Tools and closes via the same control when open", async () => {
    const user = userEvent.setup();
    const toolActive: ActiveProjection = {
      kind: "tool",
      key: "recap",
      size: "wide",
      title: "Recap",
    };
    const { onToggle, onClose, rerender } = renderHost();

    await user.click(screen.getByRole("button", { name: "Tools" }));
    expect(onToggle).toHaveBeenCalledTimes(1);

    rerender(
      <ProjectionHost
        active={toolActive}
        navigationItems={navigationItems}
        labels={{}}
        body={<p>Body</p>}
        onNavigate={vi.fn()}
        onToggle={onToggle}
        onClose={onClose}
        onExpand={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes on Escape while open", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderHost({
      active: { kind: "tool", key: "recap", size: "compact", title: "Recap" },
      body: <p>Body</p>,
      onClose,
    });

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("applies surface-projection-open on body only while open and removes it on unmount", () => {
    const active: ActiveProjection = {
      kind: "tool",
      key: "recap",
      size: "wide",
      title: "Recap",
    };
    const { unmount } = renderHost({ active, body: <p>Body</p> });

    expect(document.body).toHaveClass("surface-projection-open");
    unmount();
    expect(document.body).not.toHaveClass("surface-projection-open");
  });

  it("shows modal backdrop for tool projections but not content", () => {
    const { rerender } = renderHost({
      active: { kind: "tool", key: "recap", size: "wide", title: "Recap" },
      body: <p>Tool body</p>,
    });

    expect(document.querySelector(".surface-projection-backdrop")).not.toHaveAttribute("hidden");

    rerender(
      <ProjectionHost
        active={{
          kind: "content",
          key: "reference",
          size: "compact",
          title: "North Reach Gate",
          glanceOnly: true,
        }}
        navigationItems={navigationItems}
        labels={{}}
        body={<p>Reference body</p>}
        onNavigate={vi.fn()}
        onToggle={vi.fn()}
        onClose={vi.fn()}
        onExpand={vi.fn()}
      />,
    );

    expect(document.querySelector(".surface-projection-backdrop")).toHaveAttribute("hidden");
  });

  it("hides tool nav for content and shows Expand only for glance-only content", () => {
    const onExpand = vi.fn();
    const glanceActive: ActiveProjection = {
      kind: "content",
      key: "reference",
      size: "compact",
      title: "North Reach Gate",
      glanceOnly: true,
    };
    const { rerender } = renderHost({
      active: glanceActive,
      body: <p>Reference body</p>,
      onExpand,
    });

    const nav = document.querySelector(".surface-projection-nav");
    expect(nav).toHaveAttribute("hidden");
    expect(nav).toHaveAttribute("aria-label", "Toolbox tools");
    expect(screen.getByRole("button", { name: "Expand" })).toBeInTheDocument();

    rerender(
      <ProjectionHost
        active={{
          kind: "content",
          key: "reference",
          size: "wide",
          title: "North Reach Gate",
        }}
        navigationItems={navigationItems}
        labels={{}}
        body={<p>Reference body</p>}
        onNavigate={vi.fn()}
        onToggle={vi.fn()}
        onClose={vi.fn()}
        onExpand={onExpand}
      />,
    );

    expect(screen.queryByRole("button", { name: "Expand" })).not.toBeInTheDocument();
  });

  it.each([
    ["compact", "surface-projection-drawer--compact"],
    ["wide", "surface-projection-drawer--wide"],
    ["fullscreen", "surface-projection-drawer--fullscreen"],
  ] as const)("applies %s drawer class", (size, expectedClass) => {
    renderHost({
      active: { kind: "tool", key: "recap", size, title: "Recap" },
      body: <p>Body</p>,
    });

    const drawer = document.querySelector("#surface-projection-drawer");
    expect(drawer).toHaveClass("surface-projection-drawer");
    expect(drawer).toHaveClass(expectedClass);
  });

  it("calls onNavigate with the exact nav item id", async () => {
    const user = userEvent.setup();
    const { onNavigate } = renderHost({
      active: { kind: "tool", key: "recap", size: "wide", title: "Recap" },
      body: <p>Body</p>,
    });

    await user.click(screen.getByRole("button", { name: "Party Registry" }));
    expect(onNavigate).toHaveBeenCalledWith("party-registry");
    expect(onNavigate).toHaveBeenCalledTimes(1);
  });

  it("does not throw when Tools is clicked with an empty navigation list", async () => {
    const user = userEvent.setup();
    renderHost({ navigationItems: [] });

    await expect(user.click(screen.getByRole("button", { name: "Tools" }))).resolves.toBeUndefined();
  });
});
