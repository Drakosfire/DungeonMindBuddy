import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useMemo, useState, type ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { buildSurfaceInteractionIdentity } from "../surfaceIdentity";
import type { SurfaceInteractionIdentity } from "../types";
import { SurfaceContextHost } from "./SurfaceContextHost";
import { SurfaceContextModule } from "./SurfaceContextModule";
import { SurfaceContextAction, SurfaceContextPopover } from "./SurfaceContextPrimitives";
import { SurfaceContextProvider } from "./SurfaceContextProvider";
import { useSurfaceContextContribution } from "./useSurfaceContext";

function makeIdentity(
  surfaceId: string,
  instanceParts: readonly (string | number | boolean | null)[],
): SurfaceInteractionIdentity {
  return buildSurfaceInteractionIdentity({ surfaceId, instanceParts });
}

interface TestContributorProps {
  id: string;
  order: number;
  surfaceIdentity: SurfaceInteractionIdentity;
  label: string;
  value: string;
}

function TestContributor({
  id,
  order,
  surfaceIdentity,
  label,
  value,
}: TestContributorProps) {
  const content = useMemo(
    () => (
      <SurfaceContextModule label={label}>
        <span data-testid={`contribution-value-${id}`}>{value}</span>
      </SurfaceContextModule>
    ),
    [id, label, value],
  );

  useSurfaceContextContribution({
    id,
    order,
    surfaceIdentity,
    content,
  });

  return null;
}

function renderHost(children: ReactNode) {
  return render(
    <SurfaceContextProvider>
      {children}
      <SurfaceContextHost />
    </SurfaceContextProvider>,
  );
}

describe("SurfaceContextHost", () => {
  it("renders nothing when there are zero contributions", () => {
    renderHost(null);

    expect(screen.queryByTestId("surface-context-host")).not.toBeInTheDocument();
  });

  it("renders one contribution", () => {
    renderHost(
      <TestContributor
        id="session"
        order={0}
        surfaceIdentity={makeIdentity("plan", ["plan", "doc-1"])}
        label="Session"
        value="S27"
      />,
    );

    expect(screen.getByTestId("surface-context-host")).toBeInTheDocument();
    expect(screen.getByTestId("contribution-value-session")).toHaveTextContent("S27");
    expect(screen.getByText("Session")).toBeInTheDocument();
  });

  it("sorts several contributions by order then id", () => {
    renderHost(
      <>
        <TestContributor
          id="z-last"
          order={20}
          surfaceIdentity={makeIdentity("plan", ["plan", "doc-1"])}
          label="Z"
          value="z"
        />
        <TestContributor
          id="a-first"
          order={10}
          surfaceIdentity={makeIdentity("plan", ["plan", "doc-1"])}
          label="A"
          value="a"
        />
        <TestContributor
          id="b-tie"
          order={10}
          surfaceIdentity={makeIdentity("plan", ["plan", "doc-1"])}
          label="B"
          value="b"
        />
      </>,
    );

    const values = screen.getAllByTestId(/contribution-value-/).map((node) => node.textContent);
    expect(values).toEqual(["a", "b", "z"]);
  });

  it("removes a contribution when its contributor unmounts", () => {
    const { rerender } = render(
      <SurfaceContextProvider>
        <TestContributor
          id="session"
          order={0}
          surfaceIdentity={makeIdentity("plan", ["plan", "doc-1"])}
          label="Session"
          value="S27"
        />
        <SurfaceContextHost />
      </SurfaceContextProvider>,
    );

    expect(screen.getByTestId("contribution-value-session")).toBeInTheDocument();

    rerender(
      <SurfaceContextProvider>
        <SurfaceContextHost />
      </SurfaceContextProvider>,
    );

    expect(screen.queryByTestId("contribution-value-session")).not.toBeInTheDocument();
    expect(screen.queryByTestId("surface-context-host")).not.toBeInTheDocument();
  });

  it("updates when surface identity changes and does not keep stale identity content", () => {
    function IdentitySwitchContributor() {
      const [instancePart, setInstancePart] = useState("doc-a");

      const content = useMemo(
        () => (
          <SurfaceContextModule label="Doc">
            <span data-testid="identity-value">{instancePart}</span>
          </SurfaceContextModule>
        ),
        [instancePart],
      );

      useSurfaceContextContribution({
        id: "doc",
        order: 0,
        surfaceIdentity: makeIdentity("plan", ["plan", instancePart]),
        content,
      });

      return (
        <button type="button" onClick={() => setInstancePart("doc-b")}>
          Switch identity
        </button>
      );
    }

    renderHost(<IdentitySwitchContributor />);

    expect(screen.getByTestId("identity-value")).toHaveTextContent("doc-a");
    expect(screen.queryByText("doc-b")).not.toBeInTheDocument();

    return userEvent.setup().click(screen.getByRole("button", { name: "Switch identity" })).then(() => {
      expect(screen.getByTestId("identity-value")).toHaveTextContent("doc-b");
      expect(screen.queryByText("doc-a")).not.toBeInTheDocument();
    });
  });

  it("opens and closes the popover on trigger click and Escape", async () => {
    const user = userEvent.setup();

    function PopoverContributor() {
      const [open, setOpen] = useState(false);

      const content = useMemo(
        () => (
          <SurfaceContextModule label="More">
            <SurfaceContextPopover
              open={open}
              onOpenChange={setOpen}
              title="Details"
              trigger={
                <SurfaceContextAction onClick={() => setOpen((current) => !current)}>
                  Open
                </SurfaceContextAction>
              }
            >
              <span>Popover body</span>
            </SurfaceContextPopover>
          </SurfaceContextModule>
        ),
        [open],
      );

      useSurfaceContextContribution({
        id: "popover",
        order: 0,
        surfaceIdentity: makeIdentity("plan", ["plan", "popover"]),
        content,
      });

      return null;
    }

    renderHost(<PopoverContributor />);

    expect(screen.queryByTestId("surface-context-popover")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByTestId("surface-context-popover")).toBeInTheDocument();
    expect(screen.getByText("Popover body")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("surface-context-popover")).not.toBeInTheDocument();
  });
});
