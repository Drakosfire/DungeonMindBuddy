import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { mockContextResponse, mockQueryResponse } from "../../test/fixtures";
import { ChatModule } from "./ChatModule";

describe("ChatModule", () => {
  it("submits query and renders fast_live roll_result", async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(liveApi, "postLiveQuery").mockResolvedValue(mockQueryResponse);
    const onSuccess = vi.fn().mockResolvedValue(undefined);

    render(
      <ChatModule
        campaignId="longmont-c2"
        session={22}
        onQuerySuccess={onSuccess}
      />,
    );

    await user.type(
      screen.getByPlaceholderText(/Weather 7/),
      "Weather 7. Caelynn Nature 19.",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith(
        "Weather 7. Caelynn Nature 19.",
        "longmont-c2",
        22,
        "live",
      );
    });

    expect(screen.getByText(/Hail dent/)).toBeInTheDocument();
    expect(screen.getByText("fast_live")).toBeInTheDocument();
    expect(screen.getByText("roll_result")).toBeInTheDocument();
    expect(onSuccess).toHaveBeenCalledWith(mockQueryResponse);
  });

  it("shows context_lookup mode distinctly", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "postLiveQuery").mockResolvedValue(mockContextResponse);

    render(
      <ChatModule campaignId="longmont-c2" session={22} onQuerySuccess={vi.fn()} />,
    );

    await user.type(screen.getByPlaceholderText(/Weather 7/), "What is Lysandra feeling?");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText("context_lookup")).toBeInTheDocument();
    });
    expect(screen.getByText(/swamp as the likely source/i)).toBeInTheDocument();
    expect(screen.getByText(/Grounding \(1 admitted \/ 1 rejected\)/i)).toBeInTheDocument();
    expect(document.querySelector(".chat-response.context-lookup")).toBeTruthy();
  });
});

describe("RecordModule integration via refresh", () => {
  it("refresh callback is invoked after chat submit", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "postLiveQuery").mockResolvedValue(mockQueryResponse);
    const refresh = vi.fn().mockResolvedValue(undefined);

    render(
      <ChatModule campaignId="longmont-c2" session={22} onQuerySuccess={refresh} />,
    );
    await user.type(screen.getByPlaceholderText(/Weather 7/), "Weather 7.");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(refresh).toHaveBeenCalled());
  });
});
