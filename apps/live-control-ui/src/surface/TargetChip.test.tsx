import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TargetChip } from "./TargetChip";

describe("TargetChip", () => {
  it("renders inert span when no selection callback is provided", () => {
    render(<TargetChip targetType="roll_table" label="Travel weather table" />);
    expect(screen.getByText(/roll table · Travel weather table/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders selectable button and invokes callback", async () => {
    const user = userEvent.setup();
    const onSelectTarget = vi.fn();
    render(
      <TargetChip
        targetType="roll_table"
        label="Travel weather table"
        onSelectTarget={onSelectTarget}
      />,
    );

    await user.click(screen.getByRole("button", { name: /roll table · Travel weather table/i }));
    expect(onSelectTarget).toHaveBeenCalledTimes(1);
  });
});
