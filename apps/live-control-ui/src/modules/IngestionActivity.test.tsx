import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { IngestionActivity } from "./IngestionActivity";

afterEach(() => vi.useRealTimers());
it("shows elapsed request time without pretending intermediate results are available", () => {
  vi.useFakeTimers();
  const view = render(<IngestionActivity session={30} />);
  expect(screen.getByRole("heading")).toHaveTextContent("Working on Session 30");
  expect(screen.getByRole("timer")).toHaveTextContent("0:00 elapsed");
  act(() => vi.advanceTimersByTime(65000));
  expect(screen.getByRole("timer")).toHaveTextContent("1:05 elapsed");
  expect(screen.getByRole("status")).toHaveTextContent("Waiting for extraction and validation");
  expect(screen.getByText(/returns its results together/)).toBeInTheDocument();
  view.unmount();
  expect(vi.getTimerCount()).toBe(0);
});
