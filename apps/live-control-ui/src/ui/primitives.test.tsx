import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Badge, Button, Stack, Surface } from "./primitives";

describe("UI foundation primitives", () => {
  it("keeps Surface a labeled semantic section with its chosen tone", () => {
    render(<Surface tone="paper" aria-label="Current work">Recap</Surface>);

    const surface = screen.getByRole("region", { name: "Current work" });
    expect(surface).toHaveClass("ui-surface--paper");
    expect(surface).toHaveTextContent("Recap");
  });

  it("keeps Button native, non-submitting by default, and disabled when requested", () => {
    const onClick = vi.fn();
    render(
      <Stack direction="row">
        <Button tone="action" onClick={onClick}>Open</Button>
        <Button disabled>Unavailable</Button>
      </Stack>,
    );

    const open = screen.getByRole("button", { name: "Open" });
    expect(open).toHaveAttribute("type", "button");
    fireEvent.click(open);
    expect(onClick).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Unavailable" })).toBeDisabled();
  });

  it("renders Badge as information, not an action", () => {
    render(<Badge tone="current">Current</Badge>);

    expect(screen.getByText("Current")).toHaveClass("ui-badge--current");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("preserves Stack child order and requested layout classes", () => {
    const { container } = render(
      <Stack direction="row" gap="small" wrap>
        <span>First</span>
        <span>Second</span>
      </Stack>,
    );

    const stack = container.firstElementChild;
    expect(stack).toHaveClass("ui-stack--row", "ui-stack--gap-small", "ui-stack--wrap");
    expect(stack?.textContent).toBe("FirstSecond");
  });
});
