import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ConversationRecovery } from "./ConversationRecovery";

it("restores only on explicit action; current drafts and unresolved requests are protected", () => {
  const restore = vi.fn();
  const view = render(<ConversationRecovery question="Discuss the quarry" draft="" blocked={false} onRestore={restore} />);
  expect(restore).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button"));
  expect(restore).toHaveBeenCalledExactlyOnceWith("Discuss the quarry");
  view.rerender(<ConversationRecovery question="Discuss the quarry" draft="My unsent text" blocked={false} onRestore={restore} />);
  expect(screen.getByRole("button")).toBeDisabled();
  fireEvent.click(screen.getByRole("button"));
  view.rerender(<ConversationRecovery question="Discuss the quarry" draft="" blocked onRestore={restore} />);
  expect(screen.getByRole("button")).toBeDisabled();
  expect(restore).toHaveBeenCalledTimes(1);
});
