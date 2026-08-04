import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectionHost } from "./ProjectionHost";
import type { ActiveProjection, ProjectionHostLabels } from "./types";

const NEUTRAL_LABELS: ProjectionHostLabels = {
  toggleTitle: "Surface tools",
  closedDrawerLabel: "Surface tools",
  navigationLabel: "Tools",
  closeLabel: "Close",
  toolKicker: "Tool",
  contentKicker: "Content",
  toolTitle: "Tools",
  contentTitle: "Content",
};

const navigationItems = [
  { id: "recap", label: "Recap" },
  { id: "party-registry", label: "Party Registry" },
];

const toolActive: ActiveProjection = {
  kind: "tool",
  key: "recap",
  size: "wide",
  title: "Recap",
};

function renderHost(
  overrides: Partial<Parameters<typeof ProjectionHost>[0]> = {},
) {
  const onNavigate = vi.fn();
  const onClose = vi.fn();
  const onExpand = vi.fn();

  const result = render(
    <ProjectionHost
      active={null}
      navigationItems={navigationItems}
      labels={NEUTRAL_LABELS}
      body={null}
      onNavigate={onNavigate}
      onClose={onClose}
      onExpand={onExpand}
      {...overrides}
    />,
  );

  return { ...result, onNavigate, onClose, onExpand };
}

describe("ProjectionHost shell", () => {
  beforeEach(() => {
    document.body.classList.remove("surface-projection-open");
  });

  afterEach(() => {
    document.body.classList.remove("surface-projection-open");
  });

  it("renders nothing when active is null", () => {
    renderHost();

    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(document.querySelector(".surface-projection-host")).not.toBeInTheDocument();
  });

  it("calls onClose when the modal backdrop is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderHost({ active: toolActive, body: <p>Body</p>, onClose });

    const backdrop = document.querySelector(".surface-projection-backdrop");
    expect(backdrop).not.toHaveAttribute("hidden");
    await user.click(backdrop!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the header close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderHost({ active: toolActive, body: <p>Body</p>, onClose });

    await user.click(screen.getByRole("button", { name: NEUTRAL_LABELS.closeLabel }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onExpand when the Expand button is clicked for glance-only content", async () => {
    const user = userEvent.setup();
    const onExpand = vi.fn();
    renderHost({
      active: {
        kind: "content",
        key: "reference",
        size: "compact",
        title: "North Reach Gate",
        glanceOnly: true,
      },
      body: <p>Reference body</p>,
      onExpand,
    });

    await user.click(screen.getByRole("button", { name: "Expand" }));
    expect(onExpand).toHaveBeenCalledTimes(1);
  });

  it("removes surface-projection-open from body when active transitions open to null", () => {
    const { rerender } = renderHost({ active: toolActive, body: <p>Body</p> });
    expect(document.body).toHaveClass("surface-projection-open");

    rerender(
      <ProjectionHost
        active={null}
        navigationItems={navigationItems}
        labels={NEUTRAL_LABELS}
        body={null}
        onNavigate={vi.fn()}
        onClose={vi.fn()}
        onExpand={vi.fn()}
      />,
    );
    expect(document.body).not.toHaveClass("surface-projection-open");
  });

  it("removes the Escape listener after close and on unmount", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const { rerender, unmount } = renderHost({
      active: toolActive,
      body: <p>Body</p>,
      onClose,
    });

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
    onClose.mockClear();

    rerender(
      <ProjectionHost
        active={null}
        navigationItems={navigationItems}
        labels={NEUTRAL_LABELS}
        body={null}
        onNavigate={vi.fn()}
        onClose={onClose}
        onExpand={vi.fn()}
      />,
    );

    await user.keyboard("{Escape}");
    expect(onClose).not.toHaveBeenCalled();

    rerender(
      <ProjectionHost
        active={toolActive}
        navigationItems={navigationItems}
        labels={NEUTRAL_LABELS}
        body={<p>Body</p>}
        onNavigate={vi.fn()}
        onClose={onClose}
        onExpand={vi.fn()}
      />,
    );
    unmount();

    await user.keyboard("{Escape}");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("replaces theme tokens and data-md-theme when theme changes A to B", () => {
    const themeA = {
      themeId: "theme-a",
      tokens: { "--accent": "#111111", "--theme-a-only": "keep-me" },
    };
    const themeB = { themeId: "theme-b", tokens: { "--accent": "#222222" } };
    const { rerender } = renderHost({
      active: toolActive,
      body: <p>Body</p>,
      theme: themeA,
    });

    const host = document.querySelector(".surface-projection-host") as HTMLElement;
    expect(host).toHaveAttribute("data-md-theme", "theme-a");
    expect(host.style.getPropertyValue("--accent")).toBe("#111111");
    expect(host.style.getPropertyValue("--theme-a-only")).toBe("keep-me");

    rerender(
      <ProjectionHost
        active={toolActive}
        navigationItems={navigationItems}
        labels={NEUTRAL_LABELS}
        body={<p>Body</p>}
        theme={themeB}
        onNavigate={vi.fn()}
        onClose={vi.fn()}
        onExpand={vi.fn()}
      />,
    );

    expect(host).toHaveAttribute("data-md-theme", "theme-b");
    expect(host.style.getPropertyValue("--accent")).toBe("#222222");
    // Obsolete A-only tokens must be cleared, not merged under B.
    expect(host.style.getPropertyValue("--theme-a-only")).toBe("");
  });

  it("does not apply reference class for adversarial tool keys and keeps tool backdrop/nav behavior", () => {
    const adversarialKey = "x surface-projection-host--reference";
    renderHost({
      active: {
        kind: "tool",
        key: adversarialKey,
        size: "wide",
        title: "Evil",
      },
      body: <p>Body</p>,
    });

    const host = document.querySelector(".surface-projection-host");
    expect(host).not.toHaveClass("surface-projection-host--reference");
    expect(host).toHaveAttribute("data-projection-key", adversarialKey);

    expect(document.querySelector(".surface-projection-backdrop")).not.toHaveAttribute("hidden");
    expect(document.querySelector(".surface-projection-nav")).not.toHaveAttribute("hidden");
  });

  it("shows modal backdrop for tool projections but not content", () => {
    const { rerender } = renderHost({
      active: toolActive,
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
        labels={NEUTRAL_LABELS}
        body={<p>Reference body</p>}
        onNavigate={vi.fn()}
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
    expect(nav).toHaveAttribute("aria-label", NEUTRAL_LABELS.navigationLabel);
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
        labels={NEUTRAL_LABELS}
        body={<p>Reference body</p>}
        onNavigate={vi.fn()}
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
      active: toolActive,
      body: <p>Body</p>,
    });

    await user.click(screen.getByRole("button", { name: "Party Registry" }));
    expect(onNavigate).toHaveBeenCalledWith("party-registry");
    expect(onNavigate).toHaveBeenCalledTimes(1);
  });

  it("focuses the close button when the projection overlay opens", () => {
    renderHost({ active: toolActive, body: <p>Body</p> });

    const closeButton = screen.getByRole("button", { name: NEUTRAL_LABELS.closeLabel });
    expect(document.activeElement).toBe(closeButton);
  });
});
