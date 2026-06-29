import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { UnionSupergraphRecapProjection } from "./UnionSupergraphRecapProjection";
import { session23UnionSupergraphFixture } from "./unionSupergraphFixture";

describe("UnionSupergraphRecapProjection", () => {

  it("labels the latest graph-ingest projection source", () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
        projectionSource="latest-graph-ingest"
      />,
    );

    expect(screen.getByText(/Source: latest graph-ingest preview/i)).toBeInTheDocument();
    expect(screen.getByText(/latest preview union supergraph/i)).toBeInTheDocument();
  });

  it("renders recap without a default static explorer panel", () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    expect(screen.getByText("Session focus lens")).toBeInTheDocument();
    expect(screen.queryByLabelText("Graph node explorer")).not.toBeInTheDocument();
    expect(screen.queryByText("Pinned node")).not.toBeInTheDocument();
  });

  it("opens explorer when a recap chip is clicked", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    expect(screen.getByLabelText("Graph node explorer")).toBeInTheDocument();
    expect(screen.getByText("Expanded chip")).toBeInTheDocument();
    expect(screen.getByText("Suggested expansions")).toBeInTheDocument();
    expect(screen.getAllByText("Current session").length).toBeGreaterThan(0);
  });

  it("crawls graph via suggested expansion chips and supports back/close", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    const explorer = screen.getByLabelText("Graph node explorer");
    fireEvent.click(within(explorer).getByRole("button", { name: /Mirathorn/i }));

    const explorerAtMirathorn = screen.getByLabelText("Graph node explorer");
    expect(within(explorerAtMirathorn).getByLabelText("Explorer trail")).toHaveTextContent("Caelynn");
    expect(within(explorerAtMirathorn).getByRole("heading", { name: "Mirathorn" })).toBeInTheDocument();

    fireEvent.click(within(explorerAtMirathorn).getByRole("button", { name: "Back" }));
    const explorerAtCaelynn = screen.getByLabelText("Graph node explorer");
    expect(within(explorerAtCaelynn).getByRole("heading", { name: "Caelynn" })).toBeInTheDocument();

    fireEvent.click(within(explorerAtCaelynn).getByRole("button", { name: "Close" }));
    expect(screen.queryByLabelText("Graph node explorer")).not.toBeInTheDocument();
  });

  it("distinguishes current session from prior context evidence in explorer", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    expect(screen.getAllByText("current session").length).toBeGreaterThan(0);
    expect(screen.getAllByText("prior context").length).toBeGreaterThan(0);
  });

  it("highlights the recap paragraph selected from node evidence", async () => {
    const payload = {
      ...session23UnionSupergraphFixture,
      source_spans: [
        { span_id: "spref:session-23:p014", kind: "paragraph", ordinal: 1, text_excerpt: "Caelynn held the Mireward gate" },
      ],
    };
    render(
      <UnionSupergraphRecapProjection
        payload={payload}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    fireEvent.click(screen.getByRole("button", { name: /Held the Mireward gate/i }));

    await waitFor(() => {
      const paragraph = document.querySelector('[data-source-span-id="spref:session-23:p014"]');
      expect(paragraph).toHaveClass("recap-source-span-highlight");
    });
  });

  it("highlights source spans by text excerpt when headings and lists shift DOM order", async () => {
    const payload = {
      ...session23UnionSupergraphFixture,
      markdown: "# Session 22\n\nIntro paragraph.\n\n- A list item that renders before the target.\n\n[Caelynn](dmb-node:pc_caelynn) scouts the Mireward road.",
      source_spans: [
        { span_id: "session-22:recap:paragraph:001", kind: "paragraph", ordinal: 1, text_excerpt: "Intro paragraph." },
        { span_id: "session-22:recap:paragraph:002", kind: "paragraph", ordinal: 2, text_excerpt: "Caelynn scouts the Mireward road." },
      ],
      node_views: {
        ...session23UnionSupergraphFixture.node_views,
        pc_caelynn: {
          ...session23UnionSupergraphFixture.node_views.pc_caelynn,
          evidence_badges: [
            {
              ...session23UnionSupergraphFixture.node_views.pc_caelynn.evidence_badges[0],
              label: "Scouted the Mireward road",
              source_span_ref_id: "session-22:recap:paragraph:002",
            },
          ],
        },
      },
    };
    render(
      <UnionSupergraphRecapProjection
        payload={payload}
        selectedSessionId="session-22"
        onSelectSession={() => undefined}
        sessionOptions={["session-22"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);
    fireEvent.click(screen.getByRole("button", { name: /Scouted the Mireward road/i }));

    await waitFor(() => {
      const target = document.querySelector('[data-source-span-id="session-22:recap:paragraph:002"]');
      expect(target).toHaveClass("recap-source-span-highlight");
      expect(target?.querySelector('[data-graph-node-id="pc_caelynn"]')).toHaveTextContent("Caelynn");
      expect(target).toHaveTextContent("scouts the Mireward road.");
      expect(document.querySelector("li")).not.toHaveClass("recap-source-span-highlight");
      expect(screen.getByRole("heading", { name: "Session 22" })).not.toHaveClass("recap-source-span-highlight");
    });
  });

  it("does not attach ambiguous text excerpts to the wrong paragraph", async () => {
    const payload = {
      ...session23UnionSupergraphFixture,
      markdown: "# Session 22\n\nRepeated clue.\n\nRepeated clue.\n\n[Caelynn](dmb-node:pc_caelynn) follows a distinct trail.",
      source_spans: [
        { span_id: "session-22:recap:paragraph:001", kind: "paragraph", ordinal: 0, text_excerpt: "Repeated clue." },
      ],
      node_views: {
        ...session23UnionSupergraphFixture.node_views,
        pc_caelynn: {
          ...session23UnionSupergraphFixture.node_views.pc_caelynn,
          evidence_badges: [
            {
              ...session23UnionSupergraphFixture.node_views.pc_caelynn.evidence_badges[0],
              label: "Ambiguous repeated clue",
              source_span_ref_id: "session-22:recap:paragraph:001",
            },
          ],
        },
      },
    };
    render(
      <UnionSupergraphRecapProjection
        payload={payload}
        selectedSessionId="session-22"
        onSelectSession={() => undefined}
        sessionOptions={["session-22"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);
    fireEvent.click(screen.getByRole("button", { name: /Ambiguous repeated clue/i }));

    await waitFor(() => {
      expect(document.querySelector(".recap-source-span-highlight")).toBeNull();
      expect(document.querySelector('[data-source-span-id="session-22:recap:paragraph:001"]')).toBeNull();
    });
  });

  it("does not match short rendered nodes contained inside longer excerpts", async () => {
    const payload = {
      ...session23UnionSupergraphFixture,
      markdown: "# Session 22\n\n- road\n\n[Caelynn](dmb-node:pc_caelynn) follows a distinct trail.",
      source_spans: [
        {
          span_id: "session-22:recap:paragraph:001",
          kind: "paragraph",
          ordinal: 0,
          text_excerpt: "The party follows the road beyond the Mireward gate.",
        },
      ],
      node_views: {
        ...session23UnionSupergraphFixture.node_views,
        pc_caelynn: {
          ...session23UnionSupergraphFixture.node_views.pc_caelynn,
          evidence_badges: [
            {
              ...session23UnionSupergraphFixture.node_views.pc_caelynn.evidence_badges[0],
              label: "Short reverse-contained node",
              source_span_ref_id: "session-22:recap:paragraph:001",
            },
          ],
        },
      },
    };
    render(
      <UnionSupergraphRecapProjection
        payload={payload}
        selectedSessionId="session-22"
        onSelectSession={() => undefined}
        sessionOptions={["session-22"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);
    fireEvent.click(screen.getByRole("button", { name: /Short reverse-contained node/i }));

    await waitFor(() => {
      expect(document.querySelector("li")).not.toHaveClass("recap-source-span-highlight");
      expect(document.querySelector('[data-source-span-id="session-22:recap:paragraph:001"]')).toBeNull();
    });
  });

  it("applies role styling to recap pills", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    expect(caelynnPill).toHaveClass("role-pc");
  });

  it("shows GM planning hover card content on recap pills", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    const hoverCard = caelynnPill.parentElement?.querySelector(".recap-node-hover-card");
    expect(hoverCard).toHaveTextContent("Why now");
    expect(hoverCard).toHaveTextContent("Held the Mireward gate during the incident");
  });

  it("calls legacy opener when provided", () => {
    const onOpenLegacy = vi.fn();
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
        onOpenLegacy={onOpenLegacy}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Legacy recap preview" }));
    expect(onOpenLegacy).toHaveBeenCalledOnce();
  });
});
